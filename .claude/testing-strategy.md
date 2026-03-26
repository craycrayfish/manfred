# Testing Strategy — Manfred

## Overview

The repo has three testable layers:
1. **WhatsApp MCP plugin** — TypeScript, `plugins/whatsapp/server.ts`
2. **Hyptree dashboard** — TypeScript/Next.js, `packages/hyptree/`
3. **Python skills** — pytest already in place for twitter-manager

Markdown-based skills (most of `plugins/dev/`, `plugins/assistant/`) are prompt templates — no tests needed.

---

## Layer 1: WhatsApp Plugin (TypeScript)

### Framework
**Vitest** — preferred over Jest for TypeScript-first ESM projects; zero config, compatible with `tsx`.

```bash
cd plugins/whatsapp
npm install --save-dev vitest @vitest/coverage-v8
```

Add to `plugins/whatsapp/package.json`:
```json
"scripts": {
  "test": "vitest run",
  "test:watch": "vitest",
  "test:coverage": "vitest run --coverage"
}
```

### What to Test

The core business logic in `server.ts` is currently top-level (module-level side effects). Extract into pure functions to make them testable:

#### Unit Tests (`server.test.ts`)

| Function | Test Cases |
|---|---|
| `isAllowed(phone)` | dmPolicy=disabled → false; dmPolicy=open → true; dmPolicy=allowlist + match → true; dmPolicy=allowlist + no match → false |
| `loadAccessConfig()` | Missing file → default config; valid JSON → parsed; malformed JSON → default config |
| `resolveLid(lid)` | Matching lid-mapping file → returns E.164; no match → null; empty authDir → null |
| `inboxWrite(entry)` | Writes JSON file to inboxDir; filename has timestamp prefix |
| `inboxReadAll()` | Returns sorted entries; skips corrupt files; empty dir → [] |
| `inboxDelete(file)` | Deletes file; missing file → no throw |
| Sender extraction (messages.upsert handler) | `@s.whatsapp.net` JID → E.164 with +; already has + → unchanged; `@lid` JID → resolves via resolveLid; unknown suffix → uses raw JID |

#### Integration Tests (mocked Baileys)

- `sendNotification()` — MCP notification sends; returns true on success, false on throw
- `drainInbox()` — replays pending entries; deletes on success; leaves on failure
- Reply tool handler — missing `sock` → error response; send success → `{ content: [{text: 'Message sent'}] }`; send throws → error response with message

### Refactor Required

`server.ts` must be split to be testable. Proposed structure:
```
plugins/whatsapp/
  server.ts          # entrypoint: connects & wires
  access.ts          # loadAccessConfig, isAllowed
  inbox.ts           # inboxWrite, inboxDelete, inboxReadAll, sendNotification, drainInbox
  sender.ts          # JID → E.164 extraction, resolveLid
  mcp.ts             # MCP server setup, tool handlers
  __tests__/
    access.test.ts
    inbox.test.ts
    sender.test.ts
    mcp.test.ts
```

### Mocking Strategy

- **fs module**: use `vitest` mock or `memfs` for filesystem isolation
- **Baileys socket**: mock `makeWASocket` return value with jest-style mock object
- **MCP server**: mock `mcp.notification` and `mcp.setRequestHandler`

---

## Layer 2: Hyptree Dashboard (Next.js)

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

## Layer 3: Python Skills (pytest)

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
  test-whatsapp:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: plugins/whatsapp
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm install
      - run: npm test

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
| WhatsApp access/sender/inbox logic | 90%+ | High — security-sensitive allowlist |
| WhatsApp MCP tool handlers | 80%+ | High — core functionality |
| Python twitter-manager | 75%+ | Medium |
| Hyptree utilities | 60%+ | Low — internal tool |

---

## Implementation Order

1. **Refactor `server.ts`** into modules (prerequisite for everything else)
2. **Add vitest + write unit tests** for `access.ts`, `sender.ts`, `inbox.ts`
3. **Add mocked integration tests** for MCP tool handlers
4. **Add GitHub Actions CI**
5. **Expand Python test coverage** (opportunistic)
6. **Add hyptree tests** if dashboard grows in complexity
