---
name: brain-recall
description: Explicitly search the brain (long-term memory) for relevant notes. Use when the user asks "what do I know about X", "what did I decide about Y", or wants to look up saved preferences, decisions, or research.
argument-hint: <query> [type] — e.g. "python tooling preferences"
allowed-tools: Bash(brain:*)
---

You are searching the brain's long-term memory via the `brain` CLI. The
UserPromptSubmit hook injects memory automatically on memory-relevant prompts;
this skill is the explicit, on-demand search.

## Arguments

$ARGUMENTS

## Steps

1. Derive a concise keyword query from the arguments. If the user named a kind
   of note (preference, decision, research, etc.), pass `--type`.

2. Run the recall (JSON for parsing, then summarize for the user):

   ```bash
   brain recall "<query>" --k 8 --json
   ```

   Add `--type <type>` and/or `--tier longterm` to narrow when appropriate.

3. If there are hits, present them grouped, most relevant first:

   ```
   [preference] Prefers uv over pip/poetry  (01J9X...)
       uses uv for env + package management in Python 3.12
   ```

4. To expand on a specific note, fetch it (this also bumps its access count):

   ```bash
   brain get <id>
   brain neighbors <id> --depth 1   # related notes
   ```

5. If there are no hits, say so plainly. If the server is unreachable, `brain
   recall` returns no hits and exits 0 — tell the user the brain is offline
   rather than implying nothing is stored.

Keep it fast: one recall call, then summarize. Only fetch full notes when the
user wants detail on a specific hit.
