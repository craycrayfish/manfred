---
name: expense-aggregate
description: Extract expenses from filed receipts and update the living expenses.csv tally. Use after /expense-setup, or whenever the user asks to total up, refresh, or report on their expenses.
argument-hint: <expense-directory>
allowed-tools: Bash, Read, Write, Task, AskUserQuestion
---

Turn the receipts in `<expense-dir>/unprocessed/` into rows in `<expense-dir>/expenses.csv`, then move each receipt to `processed/`. Creates the CSV on first run, appends on every run after.

Run `/expense-setup` first if the directory has no `unprocessed/` folder.

## CSV schema — one row per receipt

`date, vendor, description, amount, currency, category, payment_method, source_file, confidence`

- `date` — ISO `YYYY-MM-DD`, the transaction date (not the file date). Empty if unreadable.
- `amount` — the total actually paid, including tax and shipping. Digits and one `.` only, no currency symbol, no thousands separators.
- `currency` — ISO code, e.g. `USD`, `GBP`, `SGD`.
- `category` — exactly one of: `meals`, `travel`, `transport`, `lodging`, `software`, `hardware`, `office`, `marketing`, `professional_services`, `utilities`, `subscriptions`, `other`, `uncategorized`. Anything else is rewritten to `uncategorized` on write.
- `confidence` — `high` / `medium` / `low`. Use `low` when the date or amount was guessed, blurred, or cut off.

## Steps

1. Resolve the directory from `$ARGUMENTS` (ask if absent). Call it `$DIR`.
2. List the work:

   ```bash
   uv run ${CLAUDE_PLUGIN_ROOT}/skills/expense-aggregate/scripts/expenses.py pending --workdir $DIR
   ```

   Anything with `already_processed: true` is a duplicate — leave it, mention it at the end.

3. **Amazon PDFs** — deterministic, no model needed. For each file in `unprocessed/amazon/`:

   ```bash
   uv run ${CLAUDE_PLUGIN_ROOT}/skills/expense-aggregate/scripts/expenses.py amazon <file>
   ```

   It returns a row with `category: uncategorized`; set the category yourself from the order description before appending.

4. **Photos, screenshots, other** — dispatch one `general-purpose` subagent per file, **in parallel** (all Task calls in a single message). Each subagent gets:

   > Read the receipt image at `<abs path>`. Return ONLY a JSON object with keys date, vendor, description, amount, currency, category, payment_method, source_file, confidence, following this schema: [paste the schema block above]. `source_file` must be exactly `<abs path>`. If a field is unreadable, use an empty string and set confidence to `low`. Do not guess an amount you cannot see.

   Non-image files under `other/` (HTML, text, CSV exports): read them yourself rather than spawning a subagent.

5. Collect every row into one JSON array. Show the user a table of what will be written, flagging `low` confidence rows and any missing amount. Ask before writing — this is a batch write.
6. Append:

   ```bash
   echo '<json array>' | uv run ${CLAUDE_PLUGIN_ROOT}/skills/expense-aggregate/scripts/expenses.py append --workdir $DIR
   ```

   Prefer a temp file over a long inline `echo` when there are many rows:
   `uv run .../expenses.py append --workdir $DIR < /tmp/expense-rows.json`

   The script dedupes by file hash, normalises the category, writes the CSV, moves each receipt into `processed/<category>/`, and updates the ledger. Files that fail to write stay in `unprocessed/`.

7. Report: rows added, running total per currency, count of `low` confidence rows worth eyeballing, and anything skipped.

## Notes

- Never hand-edit `expenses.csv` to add rows — always go through `append`, or the ledger and the CSV drift apart.
- A receipt that genuinely can't be read: leave it in `unprocessed/`, tell the user, don't invent a row.
- To re-extract a receipt, delete its hash from `.expense-ledger.json`, remove its CSV row, and move the file back to `unprocessed/`.
