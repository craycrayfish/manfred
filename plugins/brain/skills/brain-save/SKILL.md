---
name: brain-save
description: Capture durable memories from the current session into the brain (long-term memory). Use when the user says "remember this", "save that to memory", or wants to persist preferences, decisions, or research conclusions reached in this conversation.
argument-hint: [optional focus, e.g. "just my tooling preferences"]
allowed-tools: Bash(brain:*), AskUserQuestion
---

You are capturing durable long-term memory from the current session into the
brain server via the `brain` CLI (if `brain` is not on PATH, use
`plugins/brain/bin/brain` from the manfred repo). The SessionEnd hook does this automatically at
session end; this skill is the on-demand version, run against the conversation
so far.

## Arguments

$ARGUMENTS

## Phase 1: Extract candidates

Review the current conversation and extract ONLY durable, reusable facts worth
remembering across future sessions:

- **preference** — stable choices (tools, style, formats)
- **habit** — recurring working patterns
- **decision** — choices with lasting rationale
- **research** — conclusions worth keeping
- **fact / person / project / reference** — durable context

**Exclude** transient detail: the current task, files touched this session,
ephemeral debugging, one-off commands. If the user gave a focus in the
arguments, narrow to that. Prefer fewer, higher-quality items. If nothing is
worth keeping, say so and stop.

For each candidate, draft: `title` (<80 chars), `type`, `body` (1–3
self-contained sentences), `tags`, `confidence` (0–1), and optional `links`
(slugs of related notes).

## Phase 2: Confirm

Show the candidate list grouped by type:

```
Proposed memories (N):
  [preference] Prefers uv over pip/poetry — conf 0.8
  [decision]   Brain index is derived/disposable; vault is source of truth — conf 0.9
```

Ask: "Save these to the brain? (yes / edit / skip some)". Wait for explicit
confirmation before writing.

## Phase 3: Write

On confirmation, write each candidate to the inbox tier (the weekly review
elevates to long-term). Pass the body via stdin to avoid quoting issues:

```bash
echo "<body>" | brain write --title "<title>" --type <type> --tier inbox --confidence <c> --tags "<t1,t2>" --body-file -
```

Add `--source-session <id>` if known. Report what was written (count + titles).
If the server is offline, `brain write` queues to the outbox and exits 0 —
mention that the writes were queued and will flush on next connection.
