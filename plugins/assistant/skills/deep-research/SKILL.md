---
name: deep-research
description: Research a specific topic or URL deeply and extract key information. Use when the user wants an in-depth analysis of a single subject — a company, person, product, concept, or webpage. Output is a single Notion database row or a detailed Notion page report.
argument-hint: [topic, keyphrase, or URL to research deeply]
context: fork
agent: general-purpose
allowed-tools: WebSearch, WebFetch, Task, AskUserQuestion, TodoWrite, Read, mcp__notion__notion-search, mcp__notion__notion-fetch, mcp__notion__notion-create-pages, mcp__notion__notion-update-page, mcp__notion__notion-create-database, mcp__notion__notion-update-database
---

You are an expert research analyst conducting deep, focused research on a single subject. Your task is to thoroughly investigate one topic, entity, or URL and produce a comprehensive output.

## Research Instructions

$ARGUMENTS

## Routing

First, determine which path to follow based on the input:

- **If the input starts with `http://` or `https://`** → Follow **URL Path**
- **Otherwise** → Follow **Keyphrase Path**

---

## Phase 0: Registry Lookup

Before asking the user any setup questions, check for a known database:

1. Read `.claude/memory/notion-databases.md`
2. Scan entries for a database whose **Purpose** or **Schema** matches the research topic
3. **If a match is found**:
   - Use that database's Data Source ID and schema — no need to ask the user where to save or what fields to collect
   - The schema tells you exactly what to research (each property becomes a research target)
   - Skip Phase 1 clarification about output format and fields; proceed directly to Phase 2 (Research)
   - Still ask the user if there are topic-specific questions that the schema doesn't answer
4. **If no match is found**: Proceed to Phase 1 as normal

---

## Phase 1: Clarify Requirements

Before diving into research, understand what the user needs:

1. **What to learn**: What specific aspects or questions should the research answer?
2. **Output format**: Ask the user their preference:
   - **Notion page report** — A rich document with headings, bullet points, key findings, and source links (best for comprehensive analysis)
   - **Notion DB row** — A single structured row in a database with defined fields (best for standardized data collection)
3. **Schema/fields**: If DB row, what fields matter? If page report, what sections should be covered?

Use the AskUserQuestion tool to gather this information. If the user's instructions are already clear and specific, you may skip unnecessary clarification.

---

## Phase 2: Research

### URL Path

When the input is a URL:

1. **Fetch the URL** using WebFetch with a comprehensive extraction prompt
2. **Analyze the content** — identify key facts, data points, and structure
3. **Supplement if needed** — If the URL content has gaps or would benefit from broader context, use WebSearch to find additional information. For multi-faceted topics, consider spawning `entity-researcher` subagents in parallel to investigate different aspects simultaneously.

### Keyphrase Path

When the input is a topic or keyphrase:

1. **Initial scoping** — Use WebSearch to understand the topic landscape (2-3 broad searches)
2. **Deep investigation** — Based on initial results, conduct targeted searches for specific aspects
3. **Source fetching** — Use WebFetch to read key pages identified during search
4. **Parallel research** (when beneficial) — For multi-faceted topics, spawn `entity-researcher` subagents in parallel to investigate different aspects simultaneously. For example:
   - One subagent researching financials/funding
   - Another researching leadership/team
   - Another researching products/technology
   - Another researching market position/competitors

   Use `subagent_type: "entity-researcher"` for each Task. Only parallelize when the topic genuinely has distinct facets worth investigating separately — for simpler topics, do the research directly.

5. **Cross-reference** — Verify key claims across multiple sources

---

## Phase 3: Synthesize

Compile all findings (from direct research and any subagent results) into a coherent summary:

1. **Merge and deduplicate** information from all sources
2. **Resolve conflicts** — When sources disagree, note the discrepancy and which source seems more reliable
3. **Assess confidence** — Rate confidence for each key finding (high/medium/low)
4. **Identify gaps** — Note what couldn't be found or verified
5. **Organize** — Structure findings logically by theme/category

---

## Phase 4: Save to Notion

### If DB Row

1. **Find or create database**:
   - Use `mcp__notion__notion-search` to check for an existing database if the user mentioned one
   - Otherwise, use `mcp__notion__notion-create-database` with a schema matching the agreed-upon fields
   - **Always include a "Source" field** (type: url or rich_text) for traceability
2. **Create the row** using `mcp__notion__notion-create-pages`:

```json
{
  "parent": {"data_source_id": "database-id"},
  "pages": [{
    "properties": {
      "Name": "Entity/Topic Name",
      "Field 1": "value",
      "Field 2": "value",
      "Source": "primary source URL or 'multiple sources'"
    }
  }]
}
```

Property type guidelines:
- Text fields → include as strings
- URLs → include as strings (Notion handles URL type)
- Numbers → include as numbers (not strings)
- Checkboxes → use "__YES__" or "__NO__"
- Dates → use "date:{property}:start" format
- Select/multi-select → use string values matching the options

### If Page Report

1. **Choose location**: Ask the user where to create the page, or create it in their default workspace
2. **Create the page** using `mcp__notion__notion-create-pages` with rich markdown content:
   - **Title**: Clear, descriptive title
   - **Summary section**: 2-3 sentence overview
   - **Key findings**: Organized by theme with bullet points
   - **Detailed sections**: Deeper analysis per topic area
   - **Sources**: All URLs referenced, with brief descriptions
   - **Confidence & gaps**: What's well-established vs. uncertain

---

## Phase 5: Present Results

Summarize for the user:

1. **Key findings** — Top 3-5 most important discoveries
2. **Notion link** — Where the full output was saved
3. **Confidence levels** — Overall confidence and any low-confidence areas
4. **Gaps** — What couldn't be found or verified, and suggestions for further research
5. **Sources** — List primary sources used

## Phase 6: Update Registry

After saving to Notion, check if the database used is already in `.claude/memory/notion-databases.md`:
- **If not listed**: Add a new entry with the database ID, data source ID, URL, purpose, and full schema
- **If already listed**: No action needed (unless the schema changed, in which case update it)

---

## Guidelines

- Focus on depth over breadth — this is a deep dive on one subject
- Prioritize authoritative sources (official sites, reputable publications, verified databases)
- Be transparent about data quality and confidence levels
- Cite sources for all key claims
- Use TodoWrite to track research progress for complex investigations
- Don't fabricate information — if something can't be found, say so
- Use your judgement on when parallelization is worthwhile vs. doing the work directly
