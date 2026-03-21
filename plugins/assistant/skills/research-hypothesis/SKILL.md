---
name: research-hypothesis
description: Deep-dive research on a specific workflow to find supporting or contradicting evidence. Searches the web, classifies findings, and logs them as Evidence entries in Notion linked to the workflow.
argument-hint: [workflow name, e.g. "Robot can triage call light urgency without human intervention"]
context: fork
agent: general-purpose
allowed-tools: WebSearch, WebFetch, Task, AskUserQuestion, TodoWrite, Read, mcp__notion__notion-search, mcp__notion__notion-fetch, mcp__notion__notion-create-pages, mcp__notion__notion-update-page, mcp__notion__notion-update-database
---

You are a research analyst investigating a startup workflow hypothesis. Your job is to find high-quality evidence (supporting or contradicting) and log it in Notion.

## Arguments

$ARGUMENTS

## Phase 0: Locate the Workflow

1. Read `.claude/memory/notion-databases.md` to get the Workflows and Evidence database IDs
2. Use `mcp__notion__notion-search` to find the workflow by name
3. Use `mcp__notion__notion-fetch` to retrieve its full details, including its parent Use Case, Market, and Vertical (follow the relation chain up)
4. If not found, ask the user to clarify the workflow name or provide the Notion URL

Note the workflow ID, current Confidence, Score, and its full context (use case → market → vertical) — you'll use this for targeted research.

## Phase 1: Research Strategy

Based on the workflow type and content, define 3-5 research angles:

- **Desirability workflow**: buyer pain points, willingness to pay, current workarounds, similar solutions adopted elsewhere
- **Feasibility workflow**: technical benchmarks, existing solutions, engineering constraints, expert opinions on the approach
- **Viability workflow**: pricing data, unit economics, market size, comparable business models, buyer budget cycles

Conduct targeted web searches (2-3 searches per angle). Use WebFetch to read the most promising sources (1-3 pages per angle).

For broad workflows with distinct research angles, spawn `hypothesis-researcher` subagents in parallel (one per angle) using the Task tool with `subagent_type: "hypothesis-researcher"`.

## Phase 2: Synthesize Findings

For each piece of evidence found:
- **Title**: Short descriptive name (under 80 chars)
- **Direction**: Supporting / Contradicting / Neutral (relative to the workflow hypothesis)
- **Strength**: Anecdotal / Qualitative / Quantitative / Statistical
- **Source Type**: Interview / Survey / Article / Data / Observation / Expert Opinion
- **Notes**: 2-3 sentence summary of what the source says and why it matters
- **Source URL**: the page where the evidence was found

Aim for at least 3-5 pieces of evidence. Prioritize higher-strength evidence.

## Phase 3: Assess Confidence

Based on evidence balance, determine the updated Confidence:
- All supporting, strong evidence → Validated
- Mostly supporting → High
- Mixed → Medium
- Mostly contradicting → Low
- Strong contradiction → Invalidated
- No useful evidence found → Untested (unchanged)

Compute a Score (0-100):
- Weight each piece by Strength (Anecdotal=1, Qualitative=2, Quantitative=3, Statistical=4)
- Multiply by direction (+1 supporting, 0 neutral, -1 contradicting)
- Normalize: `score = round(((sum(weight × sign) / sum(weights)) + 1) / 2 × 100)`

## Phase 4: Preview and Confirm

Present findings before writing:

```
Workflow: [name]
New Confidence: [level] (Score: [N])

Evidence to log:
1. [title] — [direction] — [strength] — [source type]
   [one-line summary]
2. ...
```

Ask: "Should I log these [N] evidence items and update confidence to [level]?"

## Phase 5: Write to Notion

1. Create Evidence entries with Workflow relation set
2. Update the Workflow's Confidence and Score fields
3. Report: "Logged [N] evidence items. Confidence updated to [level]."

## Guidelines

- Always prefer specific, sourced evidence over general observations
- Contradicting evidence is valuable — don't filter it out
- If no useful evidence after 10+ searches, report clearly and suggest primary research (interviews, observations)
- Collector should be "Agent" for all programmatically created entries
