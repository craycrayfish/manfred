# Testing Strategy — Manfred

## Overview

The repo has two testable layers:
1. **Hyptree dashboard** — TypeScript/Next.js, `packages/hyptree/`
2. **Python skills** — pytest already in place for twitter-manager

Markdown-based skills (most of `plugins/dev/`, `plugins/assistant/`) are prompt templates — no tests needed.

---

## Layer 1: Hyptree Dashboard (Next.js)

### Framework
**Vitest + React Testing Library** for unit/component tests.
**Playwright** for E2E (optional, only if dashboard grows complex).

```bash
cd packages/hyptree
npm install --save-dev vitest @vitest/coverage-v8 @testing-library/react @testing-library/user-event jsdom
```

Add `vitest.config.ts`:
```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: { environment: 'jsdom', globals: true },
})
```

### What to Test

Start minimal — the dashboard is read-only (fetches from Notion). Focus on:

1. **Utility functions** — any data transformation (graph layout, node filtering)
2. **API route handlers** — if any Next.js API routes exist, test them in isolation
3. **Skip**: UI component rendering tests — low value for a single-user internal dashboard

---

## Layer 2: Python Skills (pytest)

Already configured in `twitter-manager/pyproject.toml`. Extend coverage:

| Area | What to Add |
|---|---|
| `test_twitter.py` | Edge cases: empty results, API rate limit errors, malformed responses |
| `test_grok_trends.py` | Network failure path; response parsing with missing fields |
| New skill scripts | Any new Python scripts under `plugins/*/skills/` should ship with a test file |

Run all Python tests:
```bash
uv run pytest plugins/assistant/skills/twitter-manager/
```

---

## CI/CD (GitHub Actions)

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test-hyptree:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: packages/hyptree
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm install
      - run: npm test

  test-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv run pytest plugins/assistant/skills/twitter-manager/
```

---

## Coverage Targets

| Layer | Target | Priority |
|---|---|---|
| Python twitter-manager | 75%+ | Medium |
| Hyptree utilities | 60%+ | Low — internal tool |

---

## Implementation Order

1. **Maintain GitHub Actions CI** for the Python skills
2. **Expand Python test coverage** (opportunistic)
3. **Add hyptree tests** if dashboard grows in complexity
