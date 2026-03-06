# manfred

A suite of agentic workflows for building and running a company, powered by Claude Code.

## Philosophy

Manfred treats [Claude Code](https://claude.ai/code) as an agentic orchestrator. Instead of one-off prompts, recurring business workflows — research, content creation, reflection, intelligence gathering — are codified as **skills** and **subagents** that Claude can invoke on demand.

Notion serves as the organization's source of truth. All skills write their outputs back to Notion, so knowledge is captured, searchable, and persistent across sessions.

## How it works

```
User → Claude Code → Skills / Subagents → Notion
                          ↓
                    notion-cli (internal tool)
```

- **Skills** are slash-command workflows invoked directly in Claude Code (e.g., `/deep-research`, `/entity-search`)
- **Subagents** are specialized Claude instances spawned by skills to parallelize work (e.g., one per entity being researched)
- **notion-cli** is a lightweight CLI bundled in this repo that skills and subagents use to read from and write to Notion — it is not intended for direct human use

## Skills

Skills are invoked in Claude Code as `/skill-name [arguments]`.

### `/deep-research`

Research a specific topic or URL deeply and extract key information.

Use when you want an in-depth analysis of a single subject — a company, person, product, concept, or webpage. Output is saved as a Notion database row or a detailed Notion page report.

```
/deep-research Anthropic's latest model releases
/deep-research https://example.com/competitor-pricing
```

### `/entity-search`

Find and collect data on multiple entities matching given criteria.

Use when you want to discover and build a structured dataset of companies, people, products, or other entities. Results are saved as rows in a Notion database.

```
/entity-search top 20 SNF operators in California
/entity-search https://some-directory.com/providers
```

### `/thought-partner`

A Socratic thought partner for introspection and reflection.

Conducts a guided session — asking questions, reflecting back what you say, drawing on psychology and philosophy — to help you explore your inner world. Session transcripts are saved to `outputs/thought-partner/`.

```
/thought-partner I've been feeling stuck on our go-to-market strategy
```

## Subagents

Subagents are spawned automatically by skills — they are not invoked directly by users.

| Subagent | Role |
|---|---|
| `entity-researcher` | Deep-dives on a single entity, searching multiple sources and returning structured data |
| `entity-extractor` | Extracts structured fields from a single known URL |
| `article-journalist` | Interviews the user and assembles a publication-ready article for Substack, LinkedIn, or X |
| `researcher-profiler` | Profiles an academic researcher — finds relevant publications, recent news, and generates cold outreach talking points |

## Notion as source of truth

All skills are designed to persist their outputs to Notion. The database registry at `.claude/memory/notion-databases.md` maps known databases to their schemas, so skills can automatically select the right destination without asking every time.

Supported Notion operations (used internally by skills):
- Search, fetch pages and databases
- Create and update pages
- Create and update databases
- Query databases with filters and sorts
- Append and update blocks

## Setup

**Requirements:** Node.js `>=20`, a [Notion integration token](https://www.notion.so/my-integrations)

```bash
git clone https://github.com/craycrayfish/manfred.git
cd manfred
npm install
```

Set your Notion token in a `.env` file or environment variable:

```
NOTION_TOKEN=secret_...
```

Then open the project in Claude Code. Skills become available immediately as slash commands.

## Repository structure

```
.claude/
  agents/          # Subagent definitions
  skills/          # Skill definitions (slash commands)
  memory/          # Persistent reference files (e.g., Notion database registry)
packages/
  notion-core/     # Shared Notion HTTP client
  notion-cli/      # Internal CLI used by agents to interface with Notion
```

## License

MIT
