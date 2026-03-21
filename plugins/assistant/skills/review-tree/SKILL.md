---
name: review-tree
description: Audit the hypothesis tree for MECE completeness, coverage gaps, staleness, and inconsistencies across all four levels (vertical, market, use case, workflow). Produces a structured report with prioritized recommendations.
argument-hint: [optional: vertical or market name to scope the review, or leave blank for full tree]
context: fork
agent: general-purpose
allowed-tools: AskUserQuestion, TodoWrite, Read, mcp__notion__notion-search, mcp__notion__notion-fetch
---

You are auditing the startup hypothesis tree. Your job is to identify gaps, staleness, and imbalances across all four levels (vertical → market → use case → workflow), and recommend next steps.

## Tree Structure

```
Vertical
  └── Market (MECE within vertical)
        └── Use Case (MECE within market)
              └── Workflow (testable process hypothesis)
```

## Arguments

$ARGUMENTS

## Phase 0: Fetch the Tree

1. Read `.claude/memory/notion-databases.md` to get all five database IDs
2. Fetch all pages from Verticals, Markets, Use Cases, Workflows, and Evidence databases
3. If arguments specify a vertical or market, scope the review to that subtree only
4. Build a complete picture of the tree structure

## Phase 1: MECE Analysis

For each vertical, evaluate its markets:
- **Mutual exclusivity**: Do any two markets substantially overlap?
- **Collective exhaustiveness**: What obvious segments are missing?

For each market, evaluate its use cases:
- **Mutual exclusivity**: Do any two use cases describe the same scenario?
- **Collective exhaustiveness**: Are there common jobs-to-be-done that are unrepresented?

Flag: overlaps between siblings, missing segments, thin branches (single child).

## Phase 2: Workflow Coverage

For each use case, evaluate its workflows:
- **Type coverage**: Are all three types represented (Desirability, Feasibility, Viability)?
- **Specificity**: Are workflows falsifiable? Flag vague ones (e.g., "customers will like it")
- **Status consistency**: Are validated/invalidated workflows reflected in use case status?

Flag: use cases with < 2 workflows, use cases missing a type, vague workflows.

## Phase 3: Evidence Coverage

For each workflow:
- **Untested (status Open, no evidence, > 30 days old)**: flag as stale
- **Testing > 60 days without result**: flag as stuck
- **Score/Confidence mismatch**: flag if Confidence doesn't match what Score implies

## Phase 4: Activity Analysis

- Which nodes have had no edits in > 30 days? (stale)
- Which verticals have all workflows Invalidated? (consider killing the vertical)
- Which branches are missing use cases entirely? (thin)

## Phase 5: Generate Report

```
## Hypothesis Tree Review — [date]

### Summary
- [N] verticals, [N] markets, [N] use cases, [N] workflows
- [N] workflows with evidence, [N] untested
- [N] issues found

### Critical Issues
1. [issue] — [recommendation]

### MECE Gaps
Vertical [name]:
- Missing market: [description of gap]
Market [name]:
- Missing use case: [description]
- Overlap: [use case A] and [use case B] may overlap

### Workflow Coverage Gaps
Use Case [name]: missing [type] workflow.

### Stale Items (> 30 days)
- [workflow] — last edited [date] — recommend: /research-hypothesis or park

### Recommended Next Actions (prioritized)
1. /research-hypothesis "[highest-priority untested workflow]"
2. Add [type] workflow to use case [name]
3. Park vertical [name] — all paths invalidated
```

Present the report. Offer to execute any recommended action immediately.

## Guidelines

- Be specific: name the exact node in each finding
- Prioritize by impact: MECE gaps > untested core workflows > stale items
- Don't flag intentionally parked or killed nodes
- Keep recommendations actionable (a command the user can run)
