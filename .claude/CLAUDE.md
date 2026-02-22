# Manfred - Startup Assistant

## Development Environment
- Use python 3.12+ with uv for version and package management

## Claude Code Guidelines
- Always run tests before committing: `uv run pytest`

## Notion Database Registry
- Before any research task that saves to Notion, read `.claude/memory/notion-databases.md` to check for an existing database that matches the topic.
- If a matching database exists, use it directly (skip asking the user where to save or what schema to use).
- If no match exists, follow the normal interactive flow.
- After creating a new Notion database, add an entry to `.claude/memory/notion-databases.md` using the format documented in that file.
