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

## Repository structure

```
.claude-plugin/
  marketplace.json    # Plugin catalog
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
.claude/
  CLAUDE.md           # Project instructions
  memory/             # Persistent reference files (Notion database registry)
```

## License

MIT
