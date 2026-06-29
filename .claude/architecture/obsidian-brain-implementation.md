# Implementation Plan: Obsidian Brain (CLI-first)

Companion to `obsidian-brain.md` (architecture). This is the buildable spec:
concrete layout, schemas, DDL, route/CLI contracts, hook wiring, and a
step-by-step task list per phase. Stack is locked: **Python 3.12 + uv**, **HTTP
API + `brain` CLI** (no MCP), **SQLite FTS5**, **Mac mini + launchd**.

> Conventions: relative paths used verbatim in Bash; no `\` line continuations;
> large command output redirected to files. Bump `plugins/brain` version on every
> feature PR.

---

## 0. Repository Layout

```
packages/brain-server/                # the deployable server (uv project)
├── pyproject.toml                     # deps: fastapi, uvicorn, python-frontmatter,
│                                      #       watchfiles, pydantic, ulid-py; dev: pytest, httpx, ruff
├── brain_server/
│   ├── __init__.py
│   ├── config.py                      # env: BRAIN_VAULT, BRAIN_DB, BRAIN_TOKEN, BRAIN_HOST, BRAIN_PORT
│   ├── models.py                      # pydantic: Note, NoteFrontmatter, RecallHit, ReviewItem
│   ├── repository.py                  # md <-> frontmatter; atomic writes; tier moves
│   ├── index.py                       # sqlite schema, FTS queries, edges, access bumps
│   ├── writer.py                      # single-writer asyncio queue
│   ├── watcher.py                     # watchfiles -> reconcile index
│   ├── sweeper.py                     # decay/trim job (phase 4)
│   ├── api.py                         # FastAPI app: routes + bearer auth
│   └── __main__.py                    # uvicorn entrypoint
├── tests/
│   ├── conftest.py                    # tmp vault + in-mem/temp sqlite fixtures
│   ├── test_repository.py
│   ├── test_index.py
│   ├── test_api.py
│   └── test_sweeper.py
└── deploy/
    ├── com.manfred.brain.plist        # launchd user agent
    └── README.md                      # Mac mini setup + tailnet bind notes

plugins/brain/                         # Claude Code integration (thin)
├── .claude-plugin/plugin.json         # name "brain", version 0.0.1
├── bin/brain                          # the CLI (python, stdlib-only client)
├── brain.local.json.example           # template for the uncommitted host config
├── hooks/hooks.json                   # SessionEnd capture + UserPromptSubmit recall-inject
├── scripts/
│   ├── config.py                      # resolves BRAIN_URL/TOKEN from brain.local.json (gitignored)
│   ├── capture.py                     # SessionEnd: extract memories -> brain write
│   └── recall_inject.py               # UserPromptSubmit: gated brain recall -> additionalSystemPrompt
└── skills/
    ├── brain-save/SKILL.md            # on-demand capture
    ├── brain-review/SKILL.md          # weekly review
    └── brain-recall/SKILL.md          # explicit search (optional)
```

`plugins/brain/brain.local.json` is **gitignored** (only `.example` is committed)
— it holds the per-machine host so the MagicDNS name never lands in git.

The CLI ships in `plugins/brain/bin/` (so it travels with the plugin to every
device) and is pure-stdlib (`urllib`, `json`, `argparse`) for fast startup — it
must NOT import the server package.

---

## 1. Data Contracts

### 1.1 Note on disk (`<vault>/<tier>/<id>.md`)

```yaml
---
id: 01J9X8Z3QK7M2NQ4R5S6T7U8V     # ULID, immutable, == filename stem
title: Prefers `uv` over pip/poetry for Python
type: preference                  # preference|habit|research|decision|fact|person|project|reference
tier: inbox                       # inbox|longterm|archived
status: active                    # active|archived|merged
tags: [python, tooling]
created: 2026-06-28T10:15:00Z
created_by: macbook-pro
source_session: 5d5bdc1b-fd69-430d-97db-88b4ed46a22e
last_accessed: 2026-06-28T10:15:00Z
access_count: 0
confidence: 0.7
review: pending                   # pending|elevated|discarded|merged
merged_into: null                 # ULID when status=merged
links: ["python-tooling", "uv-package-manager"]   # bare ULIDs/slugs; rendered as [[..]] in body
---
Shawn consistently reaches for `uv` for env + package management in Python 3.12
projects. Avoids pip/poetry. See [[python-tooling]].
```

Rules:
- **Filename = `{id}.md`**, folder = current `tier`. Moving tiers = move file +
  update `tier`. `id` never changes; links stay valid across tier moves.
- `links` in frontmatter is the machine edge list; inline `[[...]]` in the body
  is for humans/Obsidian. The indexer unions both into `edges`.
- All timestamps UTC ISO-8601 `Z`.

### 1.2 SQLite schema (`<vault>/.brain/index.db`)

```sql
CREATE TABLE IF NOT EXISTS notes (
  id            TEXT PRIMARY KEY,
  path          TEXT NOT NULL,
  title         TEXT NOT NULL,
  type          TEXT NOT NULL,
  tier          TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'active',
  tags          TEXT NOT NULL DEFAULT '[]',      -- json array
  created       TEXT NOT NULL,
  last_accessed TEXT NOT NULL,
  access_count  INTEGER NOT NULL DEFAULT 0,
  confidence    REAL,
  review        TEXT NOT NULL DEFAULT 'pending',
  created_by    TEXT,
  source_session TEXT,
  content_hash  TEXT NOT NULL                     -- skip re-index when unchanged
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
  title, body, tags,
  content='',                                     -- contentless; we own the rows
  tokenize='porter unicode61'
);
-- notes_fts rowid is mapped to notes via a side table:
CREATE TABLE IF NOT EXISTS fts_map (rowid INTEGER PRIMARY KEY, id TEXT UNIQUE);

CREATE TABLE IF NOT EXISTS edges (
  src_id   TEXT NOT NULL,
  dst_id   TEXT NOT NULL,
  rel_type TEXT NOT NULL DEFAULT 'relates_to',
  PRIMARY KEY (src_id, dst_id, rel_type)
);

CREATE INDEX IF NOT EXISTS idx_notes_tier ON notes(tier);
CREATE INDEX IF NOT EXISTS idx_notes_last_accessed ON notes(last_accessed);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_id);
```

The DB is **derived**: `brain_server.index.rebuild()` drops and repopulates from
the vault. `content_hash` (sha256 of frontmatter-normalized body+title) lets the
watcher skip unchanged files.

> **Build note (deviation):** the implementation uses a *standard* FTS5 table
> (not `content=''`). Contentless FTS5 requires re-supplying the original column
> values to delete/update a row, which complicates the watcher's reconcile path;
> a standard table supports `DELETE … WHERE rowid=?` directly. `fts_map`
> (now `INTEGER PRIMARY KEY AUTOINCREMENT`) still maps the integer rowid ⇄ ULID.
> Chosen for maintenance simplicity (the locked optimization goal); body-text
> duplication is negligible at personal scale.

---

## 2. HTTP API (the contract)

Base: `http://<host>:8765`. All routes require `Authorization: Bearer $BRAIN_TOKEN`
(except `/healthz`). JSON in/out. Errors: `{ "error": "<msg>" }` + 4xx/5xx.

| Method/Route | Body / Query | Returns |
|---|---|---|
| `GET /healthz` | — | `{ok, notes, outbox_hint, version}` |
| `GET /recall` | `?q&type&tier&k=8` | `{hits: [{id,title,type,tier,snippet,score}]}` — **bumps access** |
| `GET /notes/{id}` | — | full note `{frontmatter, body}` — **bumps access** |
| `GET /notes/{id}/neighbors` | `?depth=1` | `{nodes, edges}` — **bumps access** |
| `POST /notes` | `{title,type,body,tags?,links?,tier=inbox,confidence?,created_by?,source_session?}` | `{id}` — enqueues write |
| `POST /links` | `{src,dst,rel?}` | `{ok}` |
| `GET /review/queue` | `?since=7d` | `{items: [{id,title,type,confidence,created,snippet}]}` |
| `POST /review/promote` | `{id}` | `{ok}` — tier→longterm |
| `POST /review/merge` | `{ids:[...],into}` | `{ok}` |
| `POST /review/discard` | `{id}` | `{ok}` — tier→archive |
| `GET /stats` | — | counts by tier/type, decay candidates, last sweep |

Access-bumping is implemented in the read handlers ONLY. The writer queue
serializes every `POST`.

---

## 3. `brain` CLI (the only client)

`plugins/brain/bin/brain` — `#!/usr/bin/env python3`, stdlib only. Reads
`BRAIN_URL` (default `http://localhost:8765`) and `BRAIN_TOKEN` from env.

```
brain recall <query> [--type T] [--tier T] [--k 8] [--json]
brain get <id> [--json]
brain neighbors <id> [--depth 1] [--json]
brain write --title T --type T [--body-file PATH | -] [--links a,b] [--tier inbox]
            [--confidence 0.7] [--source-session S] [--json]
brain link <src> <dst> [--rel relates_to]
brain review-queue [--since 7d] [--json]
brain promote <id> | brain merge <ids...> --into <id> | brain discard <id>
brain stats [--json]
brain health
brain flush                      # drain offline outbox
```

Client behavior:
- **Writes when offline** (connection refused/timeout): append the JSON request
  (`{route, payload, ts}`) to `~/.brain/outbox.ndjson`, print a notice, exit 0.
- **`flush`** and every successful write first drain `outbox.ndjson` in order.
- **`recall` when offline**: print `{"hits": []}` (or a warning on stderr in human
  mode) and exit 0 — never block the caller.
- `--body-file -` reads stdin → avoids quoting multi-line bodies on the Bash line.
- Default output is human-readable; `--json` emits raw API JSON for hooks/skills.

---

## 4. Claude Code Wiring

### 4.1 Hooks (`plugins/brain/hooks/hooks.json`)

```jsonc
{
  "hooks": {
    "UserPromptSubmit": [
      { "matcher": "", "hooks": [
        { "type": "command",
          "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/recall_inject.py\"",
          "timeout": 4 } ] }
    ],
    "SessionEnd": [
      { "matcher": "*", "hooks": [
        { "type": "command",
          "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/capture.py\"",
          "async": true, "timeout": 30 } ] }
    ]
  }
}
```

- **`recall_inject.py`**: read hook stdin JSON → `prompt`. **Gate first** (§4.1.1)
  — only call the brain when the prompt looks memory-relevant; otherwise print
  `{}` immediately (no network, no latency). When gated in, run
  `brain recall "<prompt>" --k 5 --json` and print
  `{"additionalSystemPrompt": "Relevant long-term memory:\n- ...\n(ids: ...)"}`.
  On empty/offline/timeout → print `{}`. Must be fast and never error the turn.

#### 4.1.1 Recall-inject gate (locked)
Don't hit the brain on every prompt — gate to prompts that plausibly need memory:
- **Skip** when the prompt is trivially short, is a pure tool/command echo, or is
  a continuation acknowledgement (e.g. "yes", "go on", "thanks").
- **Trigger** when the prompt references the user's preferences/habits/past work,
  names a project/person/topic, asks "how do I/we usually…", "what did I decide…",
  "remember…", or exceeds a length threshold with question/imperative intent.
- Implement as a cheap local heuristic (regex/keyword + length) in
  `recall_inject.py` — **no LLM call in the gate** (keeps the hook sub-100ms when
  it skips). Tune the keyword list over time; err toward skipping (recall is a
  bonus, not required for correctness).
- **`capture.py`**: read hook stdin → `transcript_path`, `session_id`; apply the
  "meaningful session" gate (token/turn threshold, mirror `evaluate-session.js`);
  call the extractor (§4.2); `brain write …` each candidate. Async so it never
  blocks session teardown.

### 4.2 Extractor (`capture.py` core)

Distill the transcript into atomic memory candidates. Keep it conservative.
- Input: transcript path. Output: list of `{title, type, body, tags, confidence,
  links?}`.
- **Implementation (locked): a single headless `claude -p` call using Sonnet**
  (`claude -p --model claude-sonnet-4-6 --output-format json …`) with a strict
  JSON-schema prompt. Sonnet is the cost/quality fit for routine per-session
  extraction. The prompt asks only for durable, reusable facts (preferences,
  habits, decisions, research conclusions), forbids transient/session-specific
  detail, and returns `[]` when nothing is worth keeping. Each candidate gets a
  `confidence`. Pipe the transcript in / write candidates to a temp file, then
  feed that file to the `brain write` loop (token-efficiency rule).
- Each candidate → `brain write --title ... --type ... --body-file - --confidence
  ... --source-session $SESSION --tier inbox`.
- Idempotency: dedupe within the run by normalized title; the weekly review
  handles cross-session dupes via merge.

### 4.3 Skills

- **`brain-save`**: same extractor as `capture.py` but invoked on demand against
  the current session; shows the candidate list and writes on confirm.
- **`brain-review`**: `brain review-queue --since 7d --json > /tmp/brain-review.json`,
  cluster by `type`, present grouped; per item collect elevate/merge/discard/keep,
  then issue `brain promote|merge|discard`. Confirm before batch-applying.
- **`brain-recall`** (optional): thin `brain recall` wrapper for explicit search.

### 4.4 Host config + settings (consumer repo)

**Host config is a local, uncommitted file** — `plugins/brain/brain.local.json`
(gitignored; `brain.local.json.example` committed):

```json
{ "url": "http://m4-mini:8765", "token": "..." }
```

- The mini's MagicDNS host is `m4-mini` (SSH alias `jarvis` → `HostName m4-mini`,
  `User jarvis`, `IdentityFile ~/.ssh/jarvis`). Keeping it in the local file means
  the actual hostname never enters git.
- **Resolution order** (CLI `bin/brain` and `scripts/config.py`):
  `BRAIN_URL`/`BRAIN_TOKEN` env → else `plugins/brain/brain.local.json` → else
  `~/.brain/config.json` → else default `http://localhost:8765`.
- Permissions: add `"Bash(brain:*)"` to `.claude/settings.json` `allow`.
- Add `plugins/brain/brain.local.json` to `.gitignore`. Never commit the token.

---

## 5. Server Internals (key behaviors)

- **Single writer** (`writer.py`): an `asyncio.Queue`; one consumer task applies
  ops sequentially. `POST` handlers enqueue and await a future. Guarantees no two
  writes race on the vault or DB.
- **Atomic file write** (`repository.py`): write `"{id}.md.tmp"` then
  `os.replace()` into place; tier move = `os.replace()` across folders.
- **Indexing** (`index.py`): on write, upsert `notes`, refresh `notes_fts` via
  `fts_map`, re-parse `links` + inline `[[...]]` into `edges`. On read, `UPDATE
  notes SET last_accessed=?, access_count=access_count+1`.
- **Watcher** (`watcher.py`): `watchfiles.awatch(vault)` → for changed files,
  compare `content_hash`; reconcile (handles direct Obsidian edits). Debounced.
- **Auth** (`api.py`): dependency checks `Authorization` against `BRAIN_TOKEN`;
  constant-time compare; `/healthz` exempt.
- **Bind**: `uvicorn` host from `BRAIN_HOST` (default the tailnet IP or
  `127.0.0.1`), never `0.0.0.0`.

---

## 6. Deploy on the Mac mini (`packages/brain-server/deploy/`)

Host is the mini, SSH alias `jarvis` (`HostName m4-mini`, `User jarvis`,
`IdentityFile ~/.ssh/jarvis`). Deploy over `ssh jarvis`.

1. **Vault lives on the mini's local disk** — `BRAIN_VAULT=~/brain-vault`
   (locked: local storage, not a network/synced volume). `git init` it for backup.
   DB at `~/brain-vault/.brain/index.db`.
2. `uv sync` in `packages/brain-server` on the mini.
3. Set env (vault path, DB path, token, host/port) in the plist `EnvironmentVariables`.
   Bind `BRAIN_HOST` to the tailnet IP or `127.0.0.1` (never `0.0.0.0`).
4. `launchctl bootstrap gui/$(id -u) deploy/com.manfred.brain.plist` (KeepAlive,
   RunAtLoad, stdout/err to `~/.brain/log/`).
5. Verify on the mini: `curl -H "Authorization: Bearer $BRAIN_TOKEN" http://localhost:8765/healthz`.
6. From another tailnet device (with `plugins/brain/brain.local.json` set to
   `http://m4-mini:8765`): `brain health`.
7. Backups: cron on the mini `git add -A && git commit` daily + optional restic.
   DB is disposable (`brain rebuild` regenerates it from the vault).

`com.manfred.brain.plist` runs: `uv run python -m brain_server` with WorkingDirectory
= `packages/brain-server`.

---

## 7. Phase-by-Phase Task List

### Phase 0 — Vault schema (S) ✅ done
- [x] Vault skeleton shipped as `packages/brain-server/vault-template/` (`inbox/
      longterm/ archive/ _meta/`), copied to `~/brain-vault` at deploy.
- [x] `_meta/conventions.md` (frontmatter schema, tier rules, link rules).
- [x] Seeded `_meta/review-log.md`, `_meta/sweep-log.md` (empty headers).
- [x] Vault `.gitignore` `.brain/`; skeleton ready to commit + `git init` on the mini.

### Phase 1 — Server + CLI MVP (L) ✅ done
- [x] `packages/brain-server` uv project; deps; `config.py`, `models.py`.
- [x] `repository.py` (parse/serialize/atomic-write/tier-move) + tests.
- [x] `index.py` (DDL, upsert, FTS recall, edges, access bump, `rebuild`) + tests.
- [x] `writer.py` single-writer queue; `watcher.py` reconcile.
- [x] `api.py` routes + bearer auth; `__main__.py` uvicorn; `test_api.py` (TestClient).
- [x] `plugins/brain/bin/brain` CLI (recall/get/neighbors/write/link/review/stats/
      health + outbox/flush).
- [x] Manual e2e: write → recall → get → promote round-trips + offline flush. **15 tests green.**
- _Note:_ review routes (`/review/*`, `promote`/`merge`/`discard`) landed early in
  Phase 1 since `move_tier` made them cheap; the **review skill** is still Phase 3.

### Phase 2 — Claude Code wiring (M)
- [x] `plugins/brain/.claude-plugin/plugin.json` (v0.0.2); registered in
      `.claude-plugin/marketplace.json` + enabled in `.claude/settings.json`.
- [x] `hooks/hooks.json` (UserPromptSubmit recall-inject + async SessionEnd capture);
      `scripts/config.py` (host resolution + CLI locator); `scripts/recall_inject.py`
      (gated heuristic §4.1.1, never errors the turn); `scripts/capture.py` +
      headless Sonnet extractor (meaningful-session gate, dedupe, brain write).
- [x] `skills/brain-save` (on-demand capture, confirm-before-write),
      `skills/brain-recall` (explicit search).
- [x] Settings: `Bash(brain:*)` + `Skill(brain:*)` allow.
- [x] TDD: `test_plugin_config`, `test_recall_inject`, `test_capture` (41 tests,
      Red→Green); full suite 93 green, ruff clean.
- [ ] Deploy to Mac mini (launchd); verify cross-device `brain health` + recall-inject.
- _Note:_ recall-inject and capture **shell out to `bin/brain`** (which self-resolves
  the host), so `config.py` is mainly the CLI locator; env wiring is the CLI's job.
  Mac-mini deploy is the only open item — needs the running server + token (Phase 5).

### Phase 3 — Weekly review (M)
- [ ] Routes `/review/queue|promote|merge|discard`; repo tier-move + `review` field.
- [ ] CLI `review-queue/promote/merge/discard`; `skills/brain-review` (cluster + confirm).
- [ ] Append outcomes to `_meta/review-log.md`. Schedule weekly via `/schedule`.

### Phase 4 — Decay & trim (S–M)
- [ ] `sweeper.py`: archive non-longterm idle >90d; longterm exempt; log to `_meta/sweep-log.md`.
- [ ] `/stats` decay candidates; hard-delete eligible (archived >+30d) on review confirm.
- [ ] Schedule sweeper (launchd timer or APScheduler in-process, nightly).

### Phase 5 — Hardening (S–M)
- [ ] Backups (vault git push + restic); `brain rebuild` documented.
- [ ] `/healthz` metrics (counts, last-sweep, outbox depth); log rotation.
- [ ] launchd resilience (KeepAlive, crash backoff); README runbook.

---

## 8. Testing Strategy

- **Unit**: `repository` (round-trip md⇄frontmatter, atomic move), `index` (FTS
  ranking, access bump increments, edge parsing), `sweeper` (age boundary at 90d,
  longterm exemption).
- **API**: httpx against the FastAPI app with a temp vault + temp DB fixture;
  assert auth required, access-bump side effects, write serialization.
- **CLI**: subprocess the `brain` client against a live test server; assert
  offline outbox append + flush ordering, `--body-file -` stdin path, `--json`.
- **Hooks**: feed sample hook-stdin JSON to `recall_inject.py`/`capture.py`;
  assert `additionalSystemPrompt` shape and graceful empty/offline behavior.
- Run `uv run pytest` before every commit (repo rule).

---

## 9. Decisions (locked 2026-06-28)

1. **Vault path:** Mac mini **local storage**, `BRAIN_VAULT=~/brain-vault`,
   `git init`'d for backup; DB under `.brain/`. ✅
2. **Extractor:** headless **`claude -p` using Sonnet** (`--model claude-sonnet-4-6
   --output-format json`) with a strict JSON-schema prompt. ✅
3. **Host config:** MagicDNS name lives in an **uncommitted local file**
   `plugins/brain/brain.local.json` (gitignored; `.example` committed). The mini
   is `m4-mini` (SSH alias `jarvis`). Resolution: env → local file → `~/.brain/
   config.json` → localhost. ✅
4. **Recall-inject:** **gated** — a cheap local heuristic (§4.1.1) only calls the
   brain when the prompt looks memory-relevant; no LLM call in the gate. ✅
