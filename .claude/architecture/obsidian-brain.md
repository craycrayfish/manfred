# Architecture: Obsidian Graph as a Shared Long-Term Brain

**Status:** Draft for review · **Date:** 2026-06-28 · **Owner:** Shawn

A networked memory service backed by an Obsidian vault that multiple Claude Code
instances (across devices, over Tailscale) read from and write to. Memories flow
through a short-term inbox, a manual weekly review elevates the durable ones to
long-term, and an access-pattern-driven sweeper trims what goes stale.

---

## 1. Goals & Requirements

### Functional
- **Shared brain across devices.** Any Claude Code instance on the tailnet can
  recall and write memories against one canonical store.
- **Graph of relationships**, not flat notes: research findings, coding
  preferences/habits, decisions, people, projects — connected via links.
- **Automatic capture.** A hook distills durable memories from a session and
  files them after the session (periodically), without manual effort.
- **Buildup control via weekly review.** A review session surfaces everything
  added in the past week; the user manually elevates the keepers to long-term.
- **Access-aware decay.** Track per-memory access patterns; trim items not
  accessed in 3 months.

### Non-functional
- **Reachable only on the tailnet** — never publicly exposed.
- **Human-inspectable & portable** — the store is plain markdown openable in
  Obsidian; no lock-in to a proprietary DB.
- **Concurrency-safe** — multiple devices writing concurrently must not corrupt
  or conflict.
- **Resilient to being offline** — a device off the tailnet should still capture
  memories and flush them later.
- **Low-friction recall latency** (sub-second for typical queries).
- **Source-of-truth = the vault.** Any index/DB is a derived cache, rebuildable.

---

## 2. High-Level Architecture

```
   Device A (Claude Code)                 Device B (Claude Code)        Device C ...
   ┌──────────────────────────────┐       ┌──────────────────────┐
   │ agent ── Bash ─┐             │        │ agent ── Bash ─┐     │
   │ hooks ─────────┤             │        │ hooks ─────────┤     │
   │ cron  ─────────┤             │        │ cron  ─────────┤     │
   │                ▼             │        │                ▼     │
   │        `brain` CLI (python)  │        │        `brain` CLI   │
   │        + local outbox (offline)│      │        + outbox      │
   │  [optional: stdio MCP proxy →─┘       │                      │
   │             wraps same client]│       │                      │
   └───────────────┬──────────────┘        └──────────┬───────────┘
            HTTP (bearer token) over WireGuard         │
            └───────────────────────┬──────────────────┘
                                     ▼
              ╔══════════════════════════════════════════╗
              ║   Tailscale (MagicDNS + WireGuard;        ║
              ║   device ACLs). No public exposure.       ║
              ╚══════════════════════════════════════════╝
                                     │
              ┌──────────────────────▼──────────────────────┐
              │       BRAIN SERVER  (Mac mini, launchd)     │
              │                                             │
              │  HTTP API (FastAPI/uvicorn, bind tailnet)   │
              │  ── Write queue (single writer, serialized) │
              │  ── Repository  (markdown ⇄ frontmatter)    │
              │  ── Index/search service (SQLite FTS5)      │
              │  ── Metadata service (access, tiers)        │
              │  ── Background jobs (file-watch, sweeper)    │
              │                                             │
              │   ┌──────────────┐  watch ┌──────────────┐  │
              │   │ Obsidian Vault│ ←───→ │ SQLite (deriv)│  │
              │   │ (source truth)│       │ FTS5 + edges  │  │
              │   │  *.md + links │       │ + meta        │  │
              │   └──────────────┘        └──────────────┘  │
              │           │                                  │
              │     backups (git/restic)                     │
              └──────────────────────────────────────────────┘
```

**One server process is the single writer.** This is the key simplifier: it
serializes all writes, so the classic vault-sync merge-conflict problem
disappears. Devices never touch the vault directly — they go through the
`brain` CLI, which is an HTTP client to the server. The CLI is the **one**
client interface shared by the agent (Bash), hooks, and cron; an optional
local stdio MCP proxy can wrap it later for ergonomic agent recall (see ADR-3).

---

## 3. Components

### 3.1 Obsidian Vault (source of truth)
- A directory of atomic markdown notes — **one memory per file** — plus
  `[[wikilinks]]` that form the graph. Obsidian's graph view and backlinks
  become a free human UI for inspecting/curating the brain.
- Folders express tier/lifecycle, not topic (topic is expressed by links/tags):
  - `inbox/` — short-term, this-week captures awaiting review
  - `longterm/` — elevated, curated memories
  - `archive/` — soft-deleted (stale or discarded), kept for a grace period
  - `_meta/` — registries, review logs, sweeper audit log

### 3.2 Brain Server
The only process that touches the vault. Layers:
- **HTTP API** — a small JSON/REST surface (FastAPI + uvicorn) bound to the
  tailnet interface; the network contract behind the `brain` CLI (see §6).
- **Write queue** — an async lock / serialized queue; all mutations go through
  it. Writes are atomic (temp file + `rename`).
- **Repository** — parse/serialize markdown + YAML frontmatter; resolve links.
- **Index/search service** — SQLite FTS5 for keyword recall (no embeddings).
- **Metadata service** — bumps `last_accessed`/`access_count` on genuine
  recalls; manages tier transitions.
- **Background jobs** — a file watcher keeps the index in sync with the vault
  (so edits made directly in Obsidian are picked up), and a scheduled sweeper
  handles decay/trim.

### 3.3 Derived index (SQLite, co-located with vault)
Rebuildable from the vault at any time. Tables:
- `notes(id, path, title, type, tier, status, created, last_accessed, access_count, confidence, ...)`
- `notes_fts` — FTS5 over title + body
- `edges(src_id, dst_id, rel_type)` — the graph, parsed from links

### 3.4 Claude Code integration (this repo)
A new **`plugins/brain/`** plugin:
- `bin/brain` — the `brain` CLI (Python HTTP client; reads server URL + token
  from env). The single client used by agent, hooks, and cron.
- `hooks/hooks.json` — `SessionEnd` capture hook + `UserPromptSubmit` recall-
  injection hook (see §7).
- `skills/brain-save/` — on-demand capture; `skills/brain-review/` — weekly
  review; (optional) `skills/brain-recall/` — explicit "search my brain".
- (optional, later) `.mcp.json` — a local stdio MCP proxy wrapping the same
  client, only if agent-driven recall ergonomics warrant it.

The deployable server itself lives in **`packages/brain-server/`** (mirrors how
`packages/hyptree/` is structured as a deployable unit).

---

## 4. Data Model

Each memory note's frontmatter:

```yaml
---
id: 01J9X8Z3QK7M2N         # stable ULID — used by index + as link target
title: Prefers `uv` over pip/poetry for Python
type: preference           # preference|habit|research|decision|fact|person|project|reference
tier: inbox                # inbox|longterm|archived
status: active             # active|archived|merged
tags: [python, tooling]
created: 2026-06-28T10:15:00Z
created_by: macbook-pro     # source device
source_session: 5d5bdc1b…   # provenance for review
last_accessed: 2026-06-28T10:15:00Z
access_count: 0
confidence: 0.7            # extractor's confidence; informs review priority
review: pending            # pending|elevated|discarded|merged
links: ["[[python-tooling]]", "[[uv-package-manager]]"]
---
Shawn consistently reaches for `uv` for env + package management in Python 3.12
projects. Avoids pip/poetry. See [[python-tooling]].
```

- **Relationships** = `[[wikilinks]]` (inline or in `links`). The index parses
  them into `edges`. Typed edges (e.g. `contradicts`, `supersedes`, `relates_to`)
  can be expressed with Dataview-style inline fields (`supersedes:: [[old-note]]`)
  if needed — optional, phase 2.
- **Atomicity** keeps the graph meaningful: one claim/preference/finding per
  note, heavily linked, rather than long documents.

---

## 5. Retrieval / Search

**Locked: FTS-only.** SQLite **FTS5** over title+body, filterable by `type`/`tier`/
`tags`. FTS5 ships **inside Python's stdlib `sqlite3`** — no extra dependency, no
native extension, no embedding model. Fast, fully local/private, dead simple.
- **Graph expansion:** after a hit, optionally pull 1-hop neighbors via `edges`
  so related context comes along (`brain_neighbors`).
- **Future, optional (not in scope now):** semantic search via `sqlite-vec` +
  local embeddings, only if keyword recall proves insufficient. Deliberately
  deferred to keep the dependency surface near-stdlib.

---

## 6. Interface: `brain` CLI over an HTTP API

The agent, hooks, and cron all invoke the **`brain` CLI** (Bash); the CLI is a
thin HTTP client to the server. Every command takes `--json` for machine output
(redirect to a file per the repo's token-efficiency rules) and a human default.

| CLI command | HTTP route | Purpose | Side effects |
|---|---|---|---|
| `brain recall <query> [--type --tier --k]` | `GET /recall` | Ranked FTS search | bumps `last_accessed`, `access_count` on hits |
| `brain get <id>` | `GET /notes/{id}` | Fetch full note | bumps access |
| `brain neighbors <id> [--depth 1]` | `GET /notes/{id}/neighbors` | Graph neighbors | bumps access |
| `brain write --title --type [--body/-  --links --tier inbox --confidence]` | `POST /notes` | Create a memory (staged to inbox); body via `--body-file`/stdin to avoid arg-quoting | enqueue write |
| `brain link <src> <dst> [--rel]` | `POST /links` | Add a relationship | enqueue write |
| `brain review-queue [--since 7d]` | `GET /review/queue` | Inbox items for weekly review | none |
| `brain promote <id>` / `merge <ids> --into <id>` / `discard <id>` | `POST /review/*` | Review actions | enqueue write |
| `brain stats` | `GET /stats` | counts, decay candidates, last-sweep info | none |
| `brain health` | `GET /healthz` | liveness + outbox depth | none |

- **Body input** uses `--body-file PATH` or stdin (`-`), never a positional
  arg — sidesteps multi-line/quoting issues (and the repo's no-`\` Bash rule).
- **Offline:** any write command, when the server is unreachable, appends the
  request to the **local outbox** and exits 0; `brain flush` (and the next write)
  drains it. `brain recall` degrades gracefully (empty result + warning) so the
  agent never blocks on an offline brain.
- Access bumping happens **only on genuine recall paths** (`recall`/`get`/
  `neighbors`) — never on index rebuilds, reviews, or sweeps — so the decay
  signal stays honest.

The HTTP routes are also the contract for the optional stdio MCP proxy (ADR-3),
which would map `brain_recall` → `GET /recall`, etc.

---

## 7. Write Path (the capture hook)

Capture must distill, not dump. **Locked: two triggers** — automatic at
`SessionEnd`, and on-demand via an explicit skill. Two-step, mirroring the repo's
existing `evaluate-session.js` / `session-end.js` pattern:

1. **Triggers.**
   - **Automatic — `SessionEnd` hook (throttled).** Fires once per session,
     non-blocking; skips trivial sessions (reuse the "meaningful session"
     heuristic in `evaluate-session.js`). Hands the transcript to extraction.
   - **On-demand — `/brain-save` skill.** Lets you flush memories from the
     current session whenever you want, without waiting for session end (e.g.
     mid-long-session, or to force-capture a specific decision).
2. **Extraction.** A small Claude pass distills durable candidate memories
   (preferences, habits, research findings, decisions) with a `type` +
   `confidence`, then runs `brain write … --tier inbox` for each, tagged with
   `source_session` + `created_by` device.

No time-based/periodic flush — `SessionEnd` + explicit skill cover it and keep
the trigger model simple.

### 7.1 Read Path (recall-injection hook)

Because a CLI can't guarantee the *agent* will proactively recall, reliability
comes from a hook, not agent discretion:

- **`UserPromptSubmit` hook (throttled).** On each prompt, runs
  `brain recall "<prompt>" --k 5 --json` and injects the top hits into context
  via `additionalSystemPrompt` (same mechanism the repo's WhatsApp hook in
  `.claude/settings.json` already uses). The brain is thus *always consulted*,
  with zero reliance on the model remembering to search.
- Kept cheap: small `--k`, short timeout, and the CLI degrades to empty on miss/
  offline so a slow or down brain never stalls a turn.
- The agent can still call `brain recall` explicitly (or via `/brain-recall`) for
  deeper, query-specific lookups mid-task.

**Offline resilience:** if the server is unreachable, write commands append to a
**local outbox** file and exit 0; the next write (or `brain flush`) drains it.
`brain recall` returns empty + a warning. This makes multi-device + intermittent
connectivity safe.

---

## 8. Tiering & Weekly Review (buildup control)

Three tiers via folders: `inbox` → `longterm` → `archive`.

- **Capture lands in `inbox/`.** High volume, low curation, expected to be noisy.
- **`/brain-review` skill (weekly):** calls `brain_review_queue(since=7d)`,
  clusters items by type/topic, and presents them. For each the user chooses:
  - **Elevate** → move to `longterm/`, set `tier=longterm`, `review=elevated`.
  - **Merge** → fold into an existing canonical note + add a link; mark source `merged`.
  - **Discard** → move to `archive/`, `review=discarded`.
  - **Keep in inbox** → leave for next week.
- Schedulable via `/schedule` or `/loop` weekly. This is the **manual filter**
  that stops inbox buildup from polluting long-term memory.

---

## 9. Access Metadata & Decay/Trim

- Every genuine recall updates `last_accessed` and `access_count` (and may log
  which device accessed it).
- **Sweeper** (scheduled job on the server, e.g. nightly):
  - `tier != longterm` AND `now − last_accessed > 90d` → move to `archive/`,
    `status=archived` (soft delete). Append to `_meta/sweep-log.md`.
  - `longterm` notes are **exempt from auto-archive** (or get a longer TTL, e.g.
    12 months) and are instead *surfaced in review* rather than auto-trimmed —
    elevation is a deliberate "keep" signal.
  - Archived > grace period (e.g. +30d) → eligible for hard delete, on the next
    review's confirmation (never silent permanent deletion).
- All trims are reversible until hard-delete and fully logged → safe to automate.

---

## 10. Deployment, Networking & Security

- **Host (locked): Mac mini** on the tailnet, always-on. Run the server as a
  **`launchd`** user agent (`~/Library/LaunchAgents/com.manfred.brain.plist`,
  `KeepAlive=true`) — native, no Docker, survives reboot/login. Vault + SQLite on
  local disk.
- **Transport (locked): plain HTTP/JSON API** reached by the `brain` CLI over
  Tailscale (ADR-3). uvicorn binds to the **Tailscale interface only** (the
  node's `100.x` address or `localhost`), never `0.0.0.0`. WireGuard already
  encrypts in transit, so `tailscale serve`/TLS is optional, not required —
  one fewer moving part. Reach it at `http://brain.<tailnet>.ts.net:8765`
  (MagicDNS) via env `BRAIN_URL`.
- **Auth (defense in depth):** Tailscale device identity + WireGuard encryption
  at the network layer **plus** an app-level bearer token (env `BRAIN_TOKEN`)
  checked by the server. Optionally restrict reach with **Tailscale ACL tags** so
  only your devices' nodes can hit the brain.
- **Backups:** vault under git (push to a private remote) and/or restic snapshots
  of vault + SQLite. SQLite is disposable (rebuildable from the vault), but
  snapshotting it speeds recovery.

---

## 11. Concurrency Model

- **Single writer:** all mutations funnel through the server's write queue →
  serialized, no inter-device write conflicts (the big win over git/Obsidian-Sync
  of the vault across devices).
- **Atomic file writes:** temp file + `rename`.
- **Concurrent reads:** unrestricted; recall is read-mostly.
- **Index consistency:** the file watcher reconciles the SQLite index after every
  write and after any direct Obsidian edit; updates are idempotent and keyed by
  note `id`.

---

## 12. Key Decisions (ADRs)

### ADR-1 — Obsidian markdown vault as the store (vs Neo4j / Notion / vector DB)
**Decision:** plain markdown + wikilinks in an Obsidian vault.
**Why:** human-inspectable, portable, git-backable, and Obsidian's graph view is
a free curation UI. A graph DB (Neo4j) adds ops weight and loses human
readability; Notion is already used elsewhere but is API-rate-limited and not a
natural graph/markdown brain. The vault stays source-of-truth; SQLite is a
throwaway derived index — best of both.

### ADR-2 — Single networked server (vs syncing the vault across devices)
**Decision:** one always-on brain server; devices reach it via the `brain` CLI
over Tailscale.
**Why:** the user explicitly wants a server, and a single writer eliminates
vault-sync merge conflicts, centralizes the index/sweeper, and gives one place
for access tracking. Cost: the server must be up; mitigated by the per-device
**offline outbox**.

### ADR-3 — `brain` CLI over an HTTP API (vs remote MCP server)  ← revised
**Decision:** the agent-facing and automation-facing contract is a **`brain`
CLI** (Bash → HTTP), **not** a remote MCP server. A local stdio MCP proxy that
wraps the same client is a documented, optional later add-on.
**Why:** the **hooks and cron sweeper cannot use MCP** (it's an agent-runtime
concept) — they need a CLI/HTTP client regardless, so a CLI is mandatory and MCP
would be a *second* interface. One CLI serves agent + hooks + cron with one auth
path and one offline outbox. It reuses the already-permissioned Bash path
(`Bash(brain:*)`), keeps tool-schema context cost ~zero, and lets large reads go
to files (matching the repo's token-efficiency rules). Recall *reliability* is
solved by the `UserPromptSubmit` recall-injection hook (§7.1) — guaranteed
consultation — rather than hoping the model calls a tool. Remote Streamable-HTTP
MCP was rejected as the most new-concept-heavy option (remote-MCP registration +
TLS + token plumbing) for the least marginal benefit given the CLI is needed
anyway. **Trade-offs accepted:** coarser Bash-level permissions (vs per-tool),
stringly-typed args (mitigated by `--json` + stdin body input), and ~100–250ms
process-spawn latency per call (acceptable; recall-inject uses a light stdlib
client). If ad-hoc agent recall ever feels clunky, add the stdio MCP proxy
(~30 lines over the same HTTP routes) — no backend change.

### ADR-4 — SQLite FTS5 as the index, no embeddings (vs vector DB / sqlite-vec)
**Decision:** single-file SQLite with **FTS5 only**, co-located with the vault.
**Why:** FTS5 is built into the stdlib `sqlite3` module — keyword recall with
**zero added dependencies** and no native extensions or embedding models. Trivial
backup, fully local, fast at personal scale (≪100k notes). Semantic search is
deferred (see §5) precisely to keep the build near-stdlib and low-maintenance.

### ADR-5 — Python 3.12 + uv for the server (vs TS/Bun like the whatsapp plugin)
**Decision:** Python 3.12 + uv, ~4 pure-Python deps.
**Why:** with FTS-only, the entire stack is near-stdlib — `sqlite3` (FTS5 built
in) + official `mcp` SDK (FastMCP, Streamable HTTP) + `python-frontmatter` +
`watchfiles`. Single process, single SQLite file, no native extensions. Aligns
with `CLAUDE.md`'s "python 3.12 + uv" mandate and optimizes for code/maintenance
simplicity. Trade-off: diverges from the TS `whatsapp` MCP plugin — acceptable
since the brain server is a standalone deployable, not an in-plugin stdio
process. The thin `plugins/brain/` integration stays config + skills only.

### ADR-6 — Three tiers with manual weekly elevation + access-based auto-trim
**Decision:** inbox → longterm (manual gate) and access-decay sweeper for the
rest.
**Why:** automatic capture is necessarily noisy; a cheap human pass weekly is the
highest-signal filter for "what's worth keeping forever," while access-based
decay handles the long tail without manual effort. Longterm is exempt from
auto-trim so deliberate keeps are never lost.

---

## 13. Phased Delivery & Effort

Rough sizing (1 dev). Each phase is independently useful.

| Phase | Scope | Size |
|---|---|---|
| **0 · Vault schema** | Create the dedicated vault; decide folder layout + frontmatter schema; seed `_meta` registries; conventions doc. No code. | S (~0.5d) |
| **1 · Server + CLI MVP** | `packages/brain-server/`: HTTP API (FastAPI/uvicorn), repository (md⇄frontmatter), SQLite **FTS5** index + file watcher, write queue, routes for recall/get/write/link, access bumping. Plus the **`brain` CLI** (HTTP client + offline outbox). Run on Mac mini, bound to tailnet; `launchd` plist. | L (~3–4d) |
| **2 · Claude Code wiring** | `plugins/brain/`: ship the `brain` CLI on path (env `BRAIN_URL`/`BRAIN_TOKEN`), `SessionEnd` capture hook + async extractor, `UserPromptSubmit` recall-injection hook, `/brain-save` on-demand skill, optional `/brain-recall`. | M (~2–3d) |
| **3 · Weekly review** | `brain_review_queue/promote/merge/discard` tools + `/brain-review` skill (cluster, present, act); schedule weekly. | M (~2d) |
| **4 · Decay & trim** | Sweeper job, archive lifecycle, `_meta/sweep-log`, `brain_stats`, hard-delete-on-confirm. | S–M (~1.5d) |
| **5 · Hardening** | Backups (git/restic), health endpoint, metrics, `launchd` resilience. (Semantic search is explicitly out of scope — see §5.) | S–M (~1.5d) |

**Walking skeleton first:** Phases 0→1→2 give a usable shared brain (capture +
recall across devices). Review (3) and decay (4) make it sustainable; 5 is polish.
Total ~10–12 dev-days (down from the original estimate now that embeddings are cut).

---

## 14. Risks & Open Questions

**Risks**
- **Capture quality.** Garbage-in from the extractor pollutes the inbox. Mitigate
  with a conservative extractor, `confidence` scoring, and the weekly review gate.
- **Server availability** is a single point of failure for *live* recall (writes
  survive via outbox). Mitigate: keep host always-on; recall degrades gracefully
  (Claude proceeds without brain if unreachable).
- **Access-tracking skew.** If reviews/rebuilds bump access, decay rots. Mitigate:
  bump only on genuine recall paths (designed in).
- **Privacy.** Memories may be sensitive → everything stays on-tailnet, stored
  as local markdown + SQLite; no external API ever sees memory content (the only
  LLM call is the on-device extractor over the local transcript).

**Decisions (locked 2026-06-28)**
1. **Host:** Mac mini, `launchd` user agent. ✅
2. **Search:** SQLite **FTS5 only**; embeddings deferred. ✅
3. **Vault:** brand-new dedicated vault (not a subtree of an existing one). ✅
4. **Capture triggers:** `SessionEnd` (auto, throttled) **+** `/brain-save`
   (on-demand). No time-based flush. ✅
5. **Stack:** Python 3.12 + uv; deps `fastapi`, `uvicorn`, `python-frontmatter`,
   `watchfiles`, stdlib `sqlite3` (FTS5). ✅
6. **Interface:** `brain` CLI over an HTTP API — **not** MCP (ADR-3). Recall
   reliability via a `UserPromptSubmit` recall-injection hook. Optional stdio MCP
   proxy deferred. ✅
```
