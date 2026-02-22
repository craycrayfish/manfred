# Claude Memory Directory

This directory contains persistent reference files that Claude reads before performing tasks. These files act as a shared knowledge base across sessions.

## Files

- **notion-databases.md** — Registry of known Notion databases with their IDs, schemas, and usage notes. Skills like `deep-research` and `entity-search` consult this file to automatically select the right database instead of asking the user every time.

## Conventions

- Keep entries accurate and up-to-date. After creating a new Notion database via a skill, add it to the relevant registry file.
- Remove entries for databases that have been deleted.
- Use the standard entry format documented at the top of each registry file.
