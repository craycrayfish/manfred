---
name: orchestrate
description: Sequentially calls agents for complex development tasks.
---

# Orchestrate Command

Sequential agent workflow for complex tasks.

## Usage

`/orchestrate [workflow-type] [task-description]`

## Workflow Types

Where `code-reviewer` is found, use the most appropriate agent such as `py-reviewer` depending on the coding language used.

For any task that involves front-end code (React, HTML/CSS, TypeScript UI, component libraries, etc.), replace `codex-dev` with `gemini-dev` in the workflow below.

### feature
Full feature implementation workflow:
```
planner -> codex-dev -> code-reviewer -> security-reviewer
```
If front-end:
```
planner -> gemini-dev -> agent-browser (if UI impact) -> code-reviewer -> security-reviewer
```

### bugfix
Bug investigation and fix workflow:
```
planner -> codex-dev -> code-reviewer
```
If front-end:
```
planner -> gemini-dev -> agent-browser (if UI impact) -> code-reviewer
```

### refactor
Safe refactoring workflow:
```
architect -> code-reviewer -> codex-dev
```
If front-end:
```
architect -> code-reviewer -> gemini-dev -> agent-browser (if UI impact)
```

### Front-End Integration Check (agent-browser)

After `gemini-dev` completes, assess whether the changes have any UI impact (new components, modified layouts, changed interactions, visual changes). If yes, run an integration check using the `agent-browser` agent before proceeding to code review.

The `agent-browser` agent should:
1. Confirm the dev server is running (or start it if not)
2. Navigate to the affected pages/components
3. Exercise the changed functionality (clicks, inputs, navigation)
4. Check for console errors, broken layouts, or unexpected behaviour
5. Produce a handoff with pass/fail status and any issues found

If `agent-browser` finds issues, hand back to `gemini-dev` for fixes before continuing the chain. Skip the integration check only if the changes are purely non-visual (e.g. refactoring internal logic with no rendered output).

## Execution Pattern

For each agent in the workflow:

1. **Invoke agent** with context from previous agent
2. **Collect output** as structured handoff document
3. **Pass to next agent** in chain
4. **Aggregate results** into final report

## Handoff Document Format

Between agents, create handoff document:

```markdown
## HANDOFF: [previous-agent] -> [next-agent]

### Context
[Summary of what was done]

### Findings
[Key discoveries or decisions]

### Files Modified
[List of files touched]

### Open Questions
[Unresolved items for next agent]

### Recommendations
[Suggested next steps]
```

## Example: Feature Workflow

```
/orchestrate feature "Add user authentication"
```

Executes:

1. **Planner Agent**
   - Analyzes requirements
   - Creates implementation plan
   - Identifies dependencies
   - Output: `HANDOFF: planner -> tdd-guide`

2. **TDD Guide Agent**
   - Reads planner handoff
   - Writes tests first
   - Implements to pass tests
   - Output: `HANDOFF: tdd-guide -> code-reviewer`

3. **Code Reviewer Agent**
   - Reviews implementation
   - Checks for issues
   - Suggests improvements
   - Output: `HANDOFF: code-reviewer -> security-reviewer`

4. **Security Reviewer Agent**
   - Security audit
   - Vulnerability check
   - Final approval
   - Output: Final Report

## Final Report Format

```
ORCHESTRATION REPORT
====================
Workflow: feature
Task: Add user authentication
Agents: planner -> tdd-guide -> code-reviewer -> security-reviewer

SUMMARY
-------
[One paragraph summary]

AGENT OUTPUTS
-------------
Planner: [summary]
TDD Guide: [summary]
Code Reviewer: [summary]
Security Reviewer: [summary]

FILES CHANGED
-------------
[List all files modified]

TEST RESULTS
------------
[Test pass/fail summary]

INTEGRATION CHECK
-----------------
[PASS / FAIL / SKIPPED (non-visual change) — browser test findings]

SECURITY STATUS
---------------
[Security findings]

RECOMMENDATION
--------------
[SHIP / NEEDS WORK / BLOCKED]
```

## Parallel Execution

For independent checks, run agents in parallel:

```markdown
### Parallel Phase
Run simultaneously:
- code-reviewer (quality)
- security-reviewer (security)
- architect (design)

### Merge Results
Combine outputs into single report
```

## Arguments

$ARGUMENTS:
- `feature <description>` - Full feature workflow
- `bugfix <description>` - Bug fix workflow
- `refactor <description>` - Refactoring workflow
- `security <description>` - Security review workflow
- `custom <agents> <description>` - Custom agent sequence

## Custom Workflow Example

```
/orchestrate custom "architect,tdd-guide,code-reviewer" "Redesign caching layer"
```

## Tips

1. **Start with planner** for complex features
2. **Always include code-reviewer** before merge
3. **Use security-reviewer** for auth/payment/PII
4. **Keep handoffs concise** - focus on what next agent needs
5. **Run verification** between agents if needed
6. **Use gemini-dev for front-end** — any task touching React, HTML/CSS, or UI components should route through gemini-dev instead of codex-dev
7. **Run agent-browser after gemini-dev** — always do an integration check if the change has any rendered UI impact; skip only for purely internal refactors
