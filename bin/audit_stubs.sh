#!/bin/bash
# audit_stubs.sh
# Scans the codebase for "AI Shortcuts" and placeholders.
# Exit with error if any are found.

PATTERNS=("NotImplementedException" "TODO:" "FIXME:" "STUB")
FOUND_STUBS=0

echo "🔍 Auditing for AI Shortcuts and Stubs..."

for pattern in "${PATTERNS[@]}"; do
    # Search recursively, case-insensitive, excluding core agent config
    matches=$(grep -rEi "$pattern" . --exclude-dir=".git" --exclude-dir=".gemini" --exclude-dir=".agent" --exclude-dir="node_modules")

    if [ -n "$matches" ]; then
        echo "❌ Found pattern '$pattern' in the following files:"
        echo "$matches"
        FOUND_STUBS=1
    fi
done

if [ "$FOUND_STUBS" -eq 1 ]; then
    echo "FAILED: System contains forbidden placeholders or stubs."
    exit 1
else
    echo "✅ No stubs found. Quality Gate Passed."
    exit 0
fi
