---
name: log-evidence
description: Quickly add a piece of evidence to a workflow. Use when you already have the evidence (an interview, URL, data point) and want to log it without doing a full research pass.
argument-hint: [workflow name and evidence, e.g. "Robot triage workflow — interview with DON confirmed staff would use it"]
context: fork
agent: general-purpose
allowed-tools: WebFetch, AskUserQuestion, Read, mcp__notion__notion-search, mcp__notion__notion-fetch, mcp__notion__notion-create-pages, mcp__notion__notion-update-page
---

You are logging a piece of evidence to the hypothesis tree. Your job is to find the right workflow in Notion, gather the evidence details, and write it.

## Arguments

$ARGUMENTS

## Phase 0: Locate the Workflow

1. Read `.claude/memory/notion-databases.md` to get the Workflows and Evidence database IDs
2. Parse the arguments to identify:
   - The **workflow name** (the process being evaluated)
   - The **evidence** (what was observed or found)
3. Use `mcp__notion__notion-search` to find the workflow by name
4. If multiple matches, ask the user to clarify

## Phase 1: Gather Evidence Details

If not clear from the arguments, ask for:

1. **Title**: Short description (under 80 chars)
2. **Direction**: Supporting, Contradicting, or Neutral to the workflow hypothesis?
3. **Strength**: Anecdotal / Qualitative / Quantitative / Statistical
4. **Source Type**: Interview / Survey / Article / Data / Observation / Expert Opinion
5. **Source URL** (if applicable)
6. **Notes**: Key details — what was said, what was found, why it matters
7. **Date collected**: When did you gather this? (default: today)
8. **Your name**: For the Collector field

If a URL is provided in the arguments, use WebFetch to read it and auto-generate the title, notes, and suggest direction/strength.

Use AskUserQuestion to collect missing fields — group all questions into one ask where possible.

## Phase 2: Confirm and Write

Show a summary before saving:

```
Adding evidence to: [workflow name]
  Title: [title]
  Direction: [direction]
  Strength: [strength]
  Source Type: [source type]
  Notes: [notes]
  Source: [url or "none"]
```

Ask: "Looks good? (yes to save, or tell me what to change)"

On confirmation:
1. Create the Evidence page with Workflow relation set
2. Optionally update Workflow Confidence if the new evidence shifts the balance
   (Ask: "Based on this, should I update confidence to [suggested level]?")
3. Report: "Evidence logged."

## Guidelines

- Collector = the user's name they provide (not "Agent" — this is human-logged)
- If a URL is provided, always fetch and read it first
- Keep the interaction fast — one AskUserQuestion for all missing fields
