# manfred

A lightweight monorepo of agentic tools built around a single Notion CLI — designed for both humans and AI agents.

## Why

Most Notion integrations are either too heavy (full SDKs with opinionated abstractions) or too fragile (MCP tools that break on schema changes). Manfred replaces all of that with small, composable shell commands that map 1:1 to Notion API endpoints. An agent can call `notion invoke search` the same way a developer calls `notion search` — same binary, same output.

## Packages

| Package | Description |
|---|---|
| [`@manfred/notion-core`](packages/notion-core) | Shared Notion HTTP client |
| [`@manfred/notion-cli`](packages/notion-cli) | CLI for human and agent usage (`notion ...`) |

## Requirements

- Node.js `>=20`
- A [Notion integration token](https://www.notion.so/my-integrations) with access to the pages/databases you want to use

## Installation

```bash
git clone https://github.com/craycrayfish/manfred.git
cd manfred
npm install
```

## Configuration

Set your Notion integration token in one of two ways:

**Option 1 — Environment variable:**
```bash
export NOTION_TOKEN=secret_...
```

**Option 2 — `.env` file** (auto-loaded from the current working directory):
```
NOTION_TOKEN=secret_...
```

Both `NOTION_TOKEN` and `NOTION_API_KEY` are accepted.

To override the Notion API version (default: `2025-09-03`):
```bash
export NOTION_VERSION=2022-06-28
```

## Usage

After installation, run the CLI via `npx notion` or, if you add `packages/notion-cli/bin` to your PATH, directly as `notion`.

### Human CLI

```bash
# Search across your workspace
notion search --query "seed round notes" --page-size 10

# Fetch a page by ID
notion get-page --page-id 01234567-89ab-cdef-0123-456789abcdef

# List child blocks
notion list-blocks --block-id 01234567-89ab-cdef-0123-456789abcdef --all

# Append blocks to a page
notion append-blocks \
  --block-id 01234567-89ab-cdef-0123-456789abcdef \
  --children-file ./children.json

# Update a block
notion update-block \
  --block-id 01234567-89ab-cdef-0123-456789abcdef \
  --block-json '{"paragraph":{"rich_text":[{"text":{"content":"Updated text"}}]}}'

# Create a page in a database
notion create-page \
  --parent-json '{"database_id":"01234567-89ab-cdef-0123-456789abcdef"}' \
  --properties-json '{"Name":{"title":[{"text":{"content":"New Note"}}]}}'

# Update a page's properties
notion update-page \
  --page-id 01234567-89ab-cdef-0123-456789abcdef \
  --properties-json '{"Status":{"select":{"name":"Done"}}}'

# Fetch a database schema
notion get-data-source --data-source-id 01234567-89ab-cdef-0123-456789abcdef

# Query a database
notion query-data-source \
  --data-source-id 01234567-89ab-cdef-0123-456789abcdef \
  --page-size 25

# Create a new database
notion create-data-source \
  --parent-json '{"page_id":"01234567-89ab-cdef-0123-456789abcdef"}' \
  --title-json '[{"type":"text","text":{"content":"Ideas"}}]' \
  --properties-json '{"Name":{"title":{}},"Status":{"select":{"options":[{"name":"Backlog","color":"default"}]}}}'

# Update a database schema
notion update-data-source \
  --data-source-id 01234567-89ab-cdef-0123-456789abcdef \
  --properties-json '{"Priority":{"select":{"options":[{"name":"P1","color":"red"}]}}}'
```

#### File-based JSON flags

Every `--*-json` flag has a `--*-file` counterpart that reads JSON from a file. This is useful for large payloads:

```bash
notion append-blocks --block-id ... --children-file ./blocks.json
notion create-page --parent-json '...' --properties-file ./props.json
```

### Agent mode (`invoke`)

Use `notion invoke <operation>` to drive the CLI programmatically. Input is JSON from stdin or a flag; output is always JSON to stdout. This makes it trivial to pipe into `jq`, write to files, or chain with other commands.

```bash
# Search
printf '{"query":"customer feedback","page_size":5}\n' | notion invoke search

# Fetch a page
printf '{"page_id":"01234567-89ab-cdef-0123-456789abcdef"}\n' | notion invoke get-page

# Query a database
printf '{"data_source_id":"01234567-89ab-cdef-0123-456789abcdef","page_size":10}\n' | notion invoke query-data-source

# Create a database
printf '{"parent":{"page_id":"..."},"title":[{"type":"text","text":{"content":"Ideas"}}],"properties":{"Name":{"title":{}}}}' | notion invoke create-data-source

# Update a page
printf '{"page_id":"...","properties":{"Status":{"select":{"name":"Done"}}}}\n' | notion invoke update-page

# Input from a file
notion invoke append-blocks --input-file ./payload.json
```

#### Supported invoke operations

| Operation | Required fields |
|---|---|
| `search` | — |
| `get-page` | `page_id` |
| `create-page` | `parent` |
| `update-page` | `page_id` |
| `list-blocks` | `block_id` |
| `append-blocks` | `block_id`, `children` |
| `update-block` | `block_id`, `block` |
| `get-data-source` | `data_source_id` |
| `create-data-source` | `parent`, `title`, `properties` |
| `update-data-source` | `data_source_id` |
| `query-data-source` | `data_source_id` |

## Command reference

```
notion --help
```

```
notion search --query TEXT [--filter-json JSON] [--sort-json JSON] [--page-size N] [--start-cursor CURSOR]
notion get-page --page-id ID
notion create-page --parent-json JSON [--properties-json JSON] [--children-json JSON]
notion update-page --page-id ID [--properties-json JSON] [--archived BOOL] [--is-locked BOOL]
notion list-blocks --block-id ID [--page-size N] [--start-cursor CURSOR] [--all]
notion append-blocks --block-id ID --children-json JSON [--after BLOCK_ID]
notion update-block --block-id ID --block-json JSON
notion get-data-source --data-source-id ID
notion create-data-source --parent-json JSON --title-json JSON --properties-json JSON [--icon-json JSON] [--description-json JSON]
notion update-data-source --data-source-id ID [--title-json JSON] [--properties-json JSON] [--icon-json JSON] [--description-json JSON] [--archived BOOL] [--in-trash BOOL]
notion query-data-source --data-source-id ID [--filter-json JSON] [--sorts-json JSON] [--page-size N] [--start-cursor CURSOR]
notion invoke OPERATION [--input-json JSON | --input-file PATH]
```

## Design principles

- **Thin wrappers only.** Commands map directly to Notion API endpoints with no hidden mutation logic or schema inference.
- **Predictable for agents.** JSON in, JSON out. No interactive prompts. Errors exit non-zero with a plain message on stderr.
- **Human and agent parity.** The same binary serves both — no separate agent SDK to maintain.
- **No magic loading.** `.env` is loaded transparently; everything else is explicit via flags.

## Development

```bash
# Install dependencies
npm install

# Run tests across all packages
npm test

# Lint
npm run lint
```

## License

MIT
