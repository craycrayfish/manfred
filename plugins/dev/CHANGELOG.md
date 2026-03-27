# Changelog

## [0.2.4] - 2026-03-26

### Added
- **`gemini-dev` agent** — engineering manager subagent that delegates front-end development tasks to Gemini CLI in non-interactive mode. Plans tasks, issues structured prompts to `gemini-2.5-pro`, reviews structured `OVERVIEW`/`DETAIL`/`ERRORS` reports, and steers Gemini until work is complete.
- **`orchestrate` skill** — front-end workflows now route through `gemini-dev` instead of `codex-dev` for `feature`, `bugfix`, and `refactor` workflow types.
