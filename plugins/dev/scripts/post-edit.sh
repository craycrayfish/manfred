#!/usr/bin/env bash
# post-edit.sh — runs after every Write/Edit tool call
# Hook input is available as JSON on stdin
# Example: extract the edited file path and do something with it

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# TODO: add your post-edit logic here
# e.g. run a linter:
# npm run lint:fix -- "$FILE_PATH" 2>/dev/null || true
