#!/bin/bash
# Define paths
REPO_STORE="$HOME/.agent/skills-repos"
# We use a common skill link path that we will then point agents toward
COMMON_SKILLS_DIR="$HOME/.agent/skills"

# Check for input
if [ -z "$@" ]; then
  echo "Usage: $0 <skill-repo-name1> [skill-repo-name2]"
  exit 1
fi

for REPO_NAME in "$@"; do
  GIT_SSH_URL="git@github.corp.clover.com:clover/${REPO_NAME}.git"
  DEST_PATH="$REPO_STORE/$REPO_NAME"

  # 1. Ensure directories exist within the ...
  mkdir -p "$REPO_STORE"
  mkdir -p "$COMMON_SKILLS_DIR"

  # 2. Fresh Sync (Wipe and Clone)
  echo "Ensuring fresh state for $REPO_NAME"
  rm -rf "$DEST_PATH"
  git clone "$GIT_SSH_URL" "$DEST_PATH" || { echo "Error cloning $REPO_NAME"; continue; }

  # 3. Locate all SKILL.md files and identify their Skill Package folders
  SKILL_FILES=$(find "$DEST_PATH" -type f -name "SKILL.md")

  if [ -z "$SKILL_FILES" ]; then
    echo "Warning: No SKILL.md found in $REPO_NAME. Skipping linking for this repository."
    continue
  fi

  for SKILL_FILE in $SKILL_FILES; do
    SKILL_SRC_DIR=$(dirname "$SKILL_FILE")
    SKILL_PACKAGE_NAME=$(basename "$SKILL_SRC_DIR")

    # 4. Create the Symlinks for all Agents
    # This is the Overflow handling logic
    TARGETS=(
      "$HOME/.claude/skills/$SKILL_PACKAGE_NAME"
      "$HOME/.gemini/skills/$SKILL_PACKAGE_NAME"
      "$HOME/.gemini/antigravity/skills/$SKILL_PACKAGE_NAME"
      "$HOME/.config/github-copilot/skills/$SKILL_PACKAGE_NAME"
    )
    echo "Linking Skill Package: $SKILL_PACKAGE_NAME from $REPO_NAME"

    for T in "${TARGETS[@]}"; do
      mkdir -p "$(dirname "$T")"
      ln -sfn "$SKILL_SRC_DIR" "$T"
      echo "Linked: $T"
    done
  done
  echo "Process complete for $REPO_NAME. Skills synchronized across all agents."
done
