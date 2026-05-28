#!/usr/bin/env bash
# bin/logger.sh - Securely log prompts and responses for session audit.

# Read hook input from stdin
input=$(cat)

# Use jq to safely extract and format
prompt=$(echo "$input" | jq -r ".llm_request")
response=$(echo "$input" | jq -r ".llm_response.candidates[0].content.parts[0] | if type == \"string\" then . else .text end")

# Ensure target files exist
touch GEMINI_STACK.md GEMINI_OBSERVATIONS.md

# Log Prompt (Escaped and Code-Blocked)
{
    echo "---"
    echo "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "User Prompt:"
    echo '```json'
    echo "$prompt"
    echo '```'
    echo ""
} >> GEMINI_STACK.md

# Log Observation (Raw Markdown)
{
    echo "---"
    echo "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "Model Response:"
    echo ""
    echo "$response"
    echo ""
} >> GEMINI_OBSERVATIONS.md

# Return success to Gemini CLI
echo "{}"
exit 0
