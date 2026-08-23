---
name: expense-setup
description: Sort a directory of loose receipts (Amazon PDFs, photos of physical receipts, screenshots) into the expense working-folder layout. Use before /expense-aggregate, or whenever new receipts have been dumped into the expense folder.
argument-hint: <expense-directory>
allowed-tools: Bash, Read, AskUserQuestion
---

Sort loose receipts into the working-folder layout that `expense-aggregate` expects. This skill files things — it never extracts amounts and never touches `expenses.csv`.

## Working folder layout

```
<expense-dir>/
  unprocessed/
    amazon/         # Amazon invoice PDFs        -> deterministic regex extraction
    photos/         # photos of physical receipts -> subagent vision extraction
    screenshots/    # app/web screenshots         -> subagent vision extraction
    other/          # anything else               -> subagent, best effort
  processed/        # same four subdirs; files land here once they are in the CSV
  expenses.csv      # the living expense table
  .expense-ledger.json  # sha256 -> processed; makes reruns idempotent
```

Originals are **moved**, not copied. Filenames are preserved (slugified, `-1` suffix on collision).

## Steps

1. Resolve the target directory from `$ARGUMENTS`. If none was given, ask the user for it.
2. Preview the plan — nothing is moved yet:

   ```bash
   uv run ${CLAUDE_PLUGIN_ROOT}/skills/expense-setup/scripts/classify.py <dir> --dry-run
   ```

3. Show the user a compact summary: counts per category, plus any file whose category looks wrong. Do not paste the whole JSON if there are more than ~20 files.
4. On confirmation, run the same command without `--dry-run`.
5. Report what moved. If the user disagrees with a classification, just `mv` the file to the right `unprocessed/<category>/` directory — the categories are only routing hints for the extractor.
6. Tell the user to run `/expense-aggregate <dir>` next.

## Notes

- Files already under `unprocessed/` or `processed/` are left alone, so re-running on the same directory is safe.
- Classification: `.pdf` whose first page or filename mentions Amazon → `amazon`, other PDFs → `other`; `.jpg/.heic` → `photos`; `.png/.webp` → `screenshots` unless EXIF says it came from a camera.
