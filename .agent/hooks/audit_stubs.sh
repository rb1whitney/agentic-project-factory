#!/bin/bash
# Scans the codebase for "AI Shortcuts" and placeholders.
# Exit with error if any are found.

PATTERNS=("NotImplementedException" "TODO:" "FIXME:" "STUB")
FOUND_STUBS=0

echo "Auditing for AI Shortcuts and Stubs..."

for pattern in "${PATTERNS[@]}"; do
  matches=$(grep -rEi "$pattern" --exclude-dir=".git" --exclude-dir=".gemini" --exclude-dir=".agent" .)
  if [ -n "$matches" ]; then
    echo "Found pattern $pattern in the following files:"
    echo "$matches"
    FOUND_STUBS=1
  fi
done

if [ "$FOUND_STUBS" -eq 1 ]; then
  echo "FAILED: System contains forbidden placeholders or stubs."
  exit 1
else
  echo "No stubs found. Quality Gate Passed."
  exit 0
fi
