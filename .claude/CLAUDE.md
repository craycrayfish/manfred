# Qrobots - Startup Assistant

## Mission
Deployment of autonomous wheeled-base humanoid robots in skilled nursing facilities (SNFs) to assist caregivers with residents, specifically in the following tasks:
- **Call light triaging and response** — robots identify and respond to resident call lights, escalating to human staff as needed
- **Companionship** — robots provide social engagement and presence for residents
- **Translation** — robots facilitate communication between residents and caregivers across language barriers

> **Keeping this updated:** If the user says the mission has changed or been updated, immediately edit the Mission section above to reflect the new mission before proceeding with any other work.

## Development Environment
- Use python 3.12+ with uv for version and package management

## Claude Code Guidelines
- Always run tests before committing: `uv run pytest`
- **NEVER use backslash line continuations (`\`) in Bash commands.** Always write commands as a single line.
- **NEVER expand relative paths to absolute paths in Bash commands.** Use paths exactly as written.

## Token Efficiency
- **Write large outputs to files** instead of holding them in context. Pass the file path to subsequent CLI commands rather than re-reading the content.
- When chaining operations (e.g., research → Notion write), pipe results through temp files: write the research output to `/tmp/research-output.json`, then pass that file to the next step.
- Avoid re-fetching or re-summarizing content already retrieved in the same session — reference the file instead.
- Prefer targeted reads (specific line ranges, grep for keywords) over reading entire large files into context.
- When running CLI tools that produce verbose output, redirect to a file and only read the parts needed: `command > /tmp/out.txt`.

## Notion Integration
- **Use `notion-cli` to interface with Notion** — do NOT use the Notion MCP tools.
- Always invoke as: `npx notion <command>`
- Use the CLI for all Notion operations: searching, fetching pages, creating/updating pages and databases.

## Notion Database Registry
- Before any research task that saves to Notion, read `.claude/memory/notion-databases.md` to check for an existing database that matches the topic.
- If a matching database exists, use it directly (skip asking the user where to save or what schema to use).
- If no match exists, follow the normal interactive flow.
- After creating a new Notion database, add an entry to `.claude/memory/notion-databases.md` using the format documented in that file.

## Batch Notion Writes
- **Always confirm with the user before writing a batch of entities to Notion.** Show a preview of what will be written (entity names, count, target database) and wait for explicit approval before proceeding.
- This applies to any operation that would create or update more than one Notion page at once.

## People Database (Auto-Lookup)
- Whenever the user asks about a specific person (by name), **automatically search the People database** in Notion for an existing entry.
- If the person is found, use their existing page as context and append any new research findings to their page.
- If the person is NOT found, create a new entry in the People database with all available metadata before proceeding.
- Any relevant research discovered about an individual (background, role, affiliation, contact info, etc.) should be added to their page in the People database.
