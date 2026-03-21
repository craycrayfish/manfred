---
name: seed-tree
description: Initialize or extend the hypothesis tree with a new vertical and its MECE market segments, use cases, and workflows. Use when starting exploration of a new domain or industry. Creates the Notion databases if they don't exist yet.
argument-hint: [vertical name or industry, e.g. "Skilled Nursing Facilities" or "Healthcare Staffing"]
context: fork
agent: general-purpose
allowed-tools: WebSearch, WebFetch, AskUserQuestion, TodoWrite, Read, Write, mcp__notion__notion-search, mcp__notion__notion-fetch, mcp__notion__notion-create-pages, mcp__notion__notion-update-page, mcp__notion__notion-create-database, mcp__notion__notion-update-database
---

You are seeding or extending the startup ideation hypothesis tree. Your job is to research the target vertical, identify MECE market segments and use cases within it, and generate falsifiable workflows for each use case, then write everything to Notion.

## Tree Structure

```
Vertical (e.g., "Skilled Nursing Facilities")
  └── Market (e.g., "Call Light Response")
        └── Use Case (e.g., "Resident requests nighttime assistance")
              └── Workflow (e.g., "Robot triages urgency and routes to appropriate staff")
```

- **Vertical**: The industry or domain being explored
- **Market**: A distinct market segment within the vertical (MECE across siblings)
- **Use Case**: A specific scenario where a user/customer has a job to be done
- **Workflow**: A concrete process flow that could be automated or improved — the unit of hypothesis testing

## Arguments

$ARGUMENTS

## Phase 0: Registry Lookup

1. Read `.claude/memory/notion-databases.md`
2. Check if entries exist for all five databases: Verticals, Markets, Use Cases, Workflows, Evidence
3. If all five exist: note their database IDs and proceed to Phase 2
4. If any are missing: proceed to Phase 1 to create them

## Phase 1: Create Notion Databases (if needed)

Create a parent page called "Hypothesis Tree" (ask user for the parent page ID or use the top-level workspace).

Create five databases under that parent page:

### Verticals
Properties: Name (title), Description (rich_text), Status (select: Active/Parked/Killed), Priority (number), Owner (select: Shawn/Co-founder/Agent)

### Markets
Properties: Name (title), Description (rich_text), Status (select: Exploring/Validated/Invalidated/Parked), TAM (number, in $M), Vertical (relation → Verticals), Priority (number)

### Use Cases
Properties: Name (title), Description (rich_text), Status (select: Exploring/Validated/Invalidated/Parked), Priority (number), Owner (select: Shawn/Co-founder/Agent), Market (relation → Markets)

### Workflows
Properties: Name (title), Description (rich_text), Type (select: Desirability/Feasibility/Viability), Confidence (select: Untested/Low/Medium/High/Validated/Invalidated), Score (number), Status (select: Open/Testing/Validated/Invalidated), Owner (select: Shawn/Co-founder/Agent), Use Case (relation → Use Cases)

### Evidence
Properties: Name (title), Notes (rich_text), Direction (select: Supporting/Contradicting/Neutral), Strength (select: Anecdotal/Qualitative/Quantitative/Statistical), Source (url), Source Type (select: Interview/Survey/Article/Data/Observation/Expert Opinion), Date Collected (date), Collector (select: Shawn/Co-founder/Agent), Workflow (relation → Workflows)

After creating, update `.claude/memory/notion-databases.md` with all five database IDs.

## Phase 2: Research the Vertical

Research the target vertical:

1. Use WebSearch to understand the vertical (2-3 searches: market size, key players, pain points)
2. Identify 3-5 MECE market segments — mutually exclusive and collectively exhaustive
3. For each market, identify 2-4 use cases (specific job-to-be-done scenarios)
4. For each use case, identify 2-3 workflows (concrete process flows worth automating/improving)

## Phase 3: Generate Workflows

For each workflow, generate a falsifiable statement covering one type:

- **Desirability**: "[Persona] needs [workflow] and will actively seek a solution"
- **Feasibility**: "We can automate/improve [workflow] at the required performance and cost"
- **Viability**: "[Buyer] will pay $[price] for [workflow solution], yielding sustainable margins"

Each workflow should be:
- Falsifiable (specific enough to be proved wrong)
- Testable (can be validated with interviews, observation, or a prototype)
- Concrete (describes an actual process, not a vague goal)

## Phase 4: Preview and Confirm

Present the full proposed tree before writing:

```
Vertical: [name]
  Market: [name]
    Use Case: [name]
      W1 (Desirability): [workflow]
      W2 (Feasibility): [workflow]
    Use Case: [name]
      ...
```

Ask: "Does this look right? Any changes before I write to Notion?"

## Phase 5: Write to Notion

1. Check if this vertical already exists. If so, ask whether to add to it or skip.
2. Create in order: Vertical → Markets → Use Cases → Workflows
3. Set all relation fields (Market→Vertical, UseCase→Market, Workflow→UseCase)
4. Report: "Created 1 vertical, [N] markets, [N] use cases, [N] workflows."

## Guidelines

- Never write to Notion without user confirmation (Phase 4)
- Use "Agent" as the Owner for all programmatically created entries
- Preserve existing data — do not delete or overwrite existing entries
