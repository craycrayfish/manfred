# manfred

A Claude Code plugin monorepo containing agentic workflow plugins for Qrobots.

## Plugins

| Plugin | Description |
|--------|-------------|
| `demerzel` | Research, outreach, and intelligence gathering powered by Notion |
| `hari` | Superpowered robotics development workflows |

## Install

Add the marketplace, then install individual plugins:

```bash
/plugin marketplace add github:craycrayfish/manfred
/plugin install demerzel@manfred
/plugin install hari@manfred
```

For local development:

```bash
/plugin marketplace add ./path/to/manfred
/plugin install demerzel@manfred
```

## Packages

### `hyptree` — Hypothesis Tree Dashboard

A Next.js web dashboard for visualizing and navigating the hypothesis tree stored in Notion.

#### Prerequisites

- Node.js 18+
- A Notion integration with access to the hypothesis tree databases (created via `/seed-tree`)

#### Setup

```bash
cd packages/hyptree
npm install
cp .env.local.example .env.local
```

Edit `.env.local` and fill in your values:

```env
NOTION_API_KEY=secret_...         # From https://www.notion.so/my-integrations
NOTION_VERTICALS_DB_ID=           # Run /seed-tree to create these databases,
NOTION_MARKETS_DB_ID=             #   then copy the IDs from Notion or from
NOTION_USE_CASES_DB_ID=           #   .claude/memory/notion-databases.md
NOTION_WORKFLOWS_DB_ID=
NOTION_EVIDENCE_DB_ID=
```

#### Run

```bash
npm run dev      # http://localhost:3333
npm run build    # production build
npm run start    # serve production build on http://localhost:3333
```

## Repository structure

```
.claude-plugin/
  marketplace.json    # Plugin catalog
packages/
  hyptree/            # Hypothesis tree Next.js dashboard (port 3333)
plugins/
  demerzel/           # Research & intelligence workflows
    .claude-plugin/
      plugin.json
    skills/           # deep-research, entity-search, thought-partner
    agents/           # entity-researcher, entity-extractor, article-journalist, researcher-profiler
  hari/               # Robotics development workflows
    .claude-plugin/
      plugin.json
    skills/           # architect, tdd-dev, code-review, orchestrate, and more
    agents/           # architect, codex-dev, planner, reviewers, and more
    hooks/
    scripts/
  assistant/          # Hypothesis tree research & scoring workflows
    skills/           # seed-tree, research-hypothesis, score-hypothesis, log-evidence, review-tree
    agents/           # hypothesis-researcher
.claude/
  CLAUDE.md           # Project instructions
  memory/             # Persistent reference files (Notion database registry)
```

## License

MIT
