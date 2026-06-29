# Brain Vault Conventions

This vault is the **source of truth** for the long-term brain. The SQLite index
under `.brain/` is derived and disposable — delete it and the server rebuilds it
from these notes on boot.

## Layout

| Folder | Tier | Meaning |
|--------|------|---------|
| `inbox/` | `inbox` | Freshly captured candidates awaiting weekly review |
| `longterm/` | `longterm` | Elevated, durable memory (exempt from decay) |
| `archive/` | `archived` | Discarded / merged / decayed notes (kept for history) |
| `_meta/` | — | Conventions + review/sweep logs (not indexed as memory) |
| `.brain/` | — | Derived SQLite index (gitignored) |

## Note format

Each note is `{id}.md` where `{id}` is an immutable ULID equal to the filename
stem. The folder reflects the current tier; moving tiers moves the file and
updates the `tier` field — the `id` never changes, so links stay valid.

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
source_session: <session-id>
last_accessed: 2026-06-28T10:15:00Z   # authoritative copy lives in the index
access_count: 0                        # authoritative copy lives in the index
confidence: 0.7
review: pending                   # pending|elevated|discarded|merged
merged_into: null                 # ULID when status=merged
links: ["python-tooling"]         # machine edge list; rendered as [[..]] in body
---
Body in markdown. Inline [[wikilinks]] are unioned with `links` into the graph.
```

## Rules

- **Timestamps** are UTC ISO-8601 with a `Z` suffix.
- `links` (frontmatter) is the machine edge list; inline `[[...]]` in the body is
  for humans/Obsidian. The indexer unions both into the `edges` table.
- `last_accessed` / `access_count` are bumped in the **index** on every recall or
  fetch; the file is not rewritten per-access (avoids churn). Treat the index as
  authoritative for access telemetry.
- **Decay:** non-`longterm` notes idle for >90 days are archived by the sweeper;
  `longterm` is exempt. Elevation to `longterm` happens only via weekly review.
