---
name: score-hypothesis
description: Calculate or recalculate confidence scores for workflows based on their evidence. Scope can be a single workflow, all workflows in a use case, a market, or an entire vertical.
argument-hint: [scope — workflow name, use case name, market name, vertical name, or "all"]
context: fork
agent: general-purpose
allowed-tools: AskUserQuestion, Read, mcp__notion__notion-search, mcp__notion__notion-fetch, mcp__notion__notion-update-page
---

You are recalculating workflow confidence scores based on logged evidence.

## Scoring Algorithm

For each workflow:

1. Fetch all Evidence entries linked to it
2. For each piece:
   - **Weight** by strength: Anecdotal=1, Qualitative=2, Quantitative=3, Statistical=4
   - **Sign** by direction: Supporting=+1, Neutral=0, Contradicting=-1
3. `score = round(((sum(weight × sign) / sum(weights)) + 1) / 2 × 100)`
   - Range: 0–100, where 50 = perfectly neutral
4. Map to Confidence:
   - No evidence → Untested (score stays 50)
   - Score < 20 → Invalidated
   - Score 20–39 → Low
   - Score 40–59 → Medium
   - Score 60–79 → High
   - Score ≥ 80 → Validated

## Arguments

$ARGUMENTS

## Phase 0: Determine Scope

1. Read `.claude/memory/notion-databases.md` to get all database IDs
2. Parse arguments to determine scope:
   - Workflow name → score just that workflow
   - Use case name → score all workflows in that use case
   - Market name → score all workflows across all use cases in that market
   - Vertical name → score all workflows in the entire vertical
   - "all" → score every workflow in the tree
3. Use `mcp__notion__notion-search` to find the target entity and build the list of workflows to score

## Phase 1: Fetch Evidence and Compute Scores

For each workflow in scope:
1. Fetch all Evidence entries (filter by Workflow relation)
2. Apply the scoring algorithm
3. Record: workflow ID, current confidence, new score, new confidence level

## Phase 2: Preview

Show a table before writing:

```
Workflow                              | Old Confidence | New Score | New Confidence
--------------------------------------|---------------|-----------|---------------
[name]                                | Untested       | 72        | High
[name]                                | Medium         | 45        | Medium (no change)
[name]                                | Low            | 18        | Invalidated
```

Ask: "Update [N] workflows in Notion? (yes / no / pick specific ones)"

## Phase 3: Write Updates

For each confirmed workflow:
1. Update the Score (number) field
2. Update the Confidence (select) field
3. Note any confidence level changes

Report: "Updated [N] workflows. [N] confidence levels changed."

## Guidelines

- Only update workflows that have evidence — leave Untested workflows unchanged unless asked
- Always show a preview and get confirmation before writing
- For large batches (> 20), ask if the user wants to narrow the scope first
