# manfred

Monorepo for lightweight agentic tools, centered on one Notion CLI for both humans and agents.

## Why this exists

The goal is to replace heavyweight/fragile Notion integrations with small, composable commands that an agent can invoke directly.

## Packages

- `@manfred/notion-core`: shared Notion HTTP client.
- `@manfred/notion-cli`: single CLI for human and agent usage (`notion ...`).

## Notion API version

By default, requests send:

- `Notion-Version: 2025-09-03`

Override with `NOTION_VERSION` if needed.

## Prereqs

- Node.js `>=20`
- A Notion integration token in `NOTION_TOKEN` (or `NOTION_API_KEY`)
  (loaded automatically from `.env` if present)

## Install

```bash
npm install
```

## CLI usage

```bash
notion --help
```

Examples:

```bash
# Search
notion search --query "seed round notes" --page-size 10

# Read a page
notion get-page --page-id 01234567-89ab-cdef-0123-456789abcdef

# List child blocks
notion list-blocks --block-id 01234567-89ab-cdef-0123-456789abcdef --all

# Append paragraphs from JSON file
notion append-blocks \
  --block-id 01234567-89ab-cdef-0123-456789abcdef \
  --children-file ./children.json

# Create a page in a data source
notion create-page \
  --parent-json '{"data_source_id":"01234567-89ab-cdef-0123-456789abcdef"}' \
  --properties-json '{"Name":{"title":[{"text":{"content":"New Note"}}]}}'

# Fetch a data source schema
notion get-data-source \
  --data-source-id 01234567-89ab-cdef-0123-456789abcdef

# Create a data source (schema)
notion create-data-source \
  --parent-json '{"page_id":"01234567-89ab-cdef-0123-456789abcdef"}' \
  --title-json '[{"type":"text","text":{"content":"Ideas"}}]' \
  --properties-json '{"Name":{"title":{}},"Status":{"select":{"options":[{"name":"Backlog","color":"default"}]}}}'

# Update data source schema
notion update-data-source \
  --data-source-id 01234567-89ab-cdef-0123-456789abcdef \
  --properties-json '{"Priority":{"select":{"options":[{"name":"P1","color":"red"}]}}}'

# Query a data source
notion query-data-source \
  --data-source-id 01234567-89ab-cdef-0123-456789abcdef \
  --page-size 25
```

## Agent usage (same `notion` CLI)

Use `notion invoke <operation>` with JSON input from stdin (or `--input-json` / `--input-file`).

```bash
# Search
printf '{"query":"customer feedback","page_size":5}\n' | notion invoke search

# Fetch page
printf '{"page_id":"01234567-89ab-cdef-0123-456789abcdef"}\n' | notion invoke get-page

# Query data source
printf '{"data_source_id":"01234567-89ab-cdef-0123-456789abcdef","page_size":10}\n' | notion invoke query-data-source

# Create data source schema
printf '{"parent":{"page_id":"..."},"title":[{"type":"text","text":{"content":"Ideas"}}],"properties":{"Name":{"title":{}}}}' | notion invoke create-data-source

# Update page properties
printf '{"page_id":"...","properties":{"Status":{"select":{"name":"Done"}}}}\n' | notion invoke update-page
```

Supported invoke operations:

- `search`
- `get-page`
- `list-blocks`
- `append-blocks`
- `create-page`
- `update-page`
- `get-data-source`
- `create-data-source`
- `update-data-source`
- `query-data-source`
- `update-block`

## Notes

- Commands are intentionally thin wrappers over official Notion endpoints.
- For safety, these tools do not attempt schema inference or hidden mutation logic.
- You control payload shape directly, which is better for predictable agent behavior.
