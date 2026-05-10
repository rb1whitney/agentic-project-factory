---
name: codebase-recon
description: Git forensics tool for identifying hotspots, churn, and knowledge gaps before reading code.
related_skills: ["@architecture-specialist", "@sre-specialist"]
auto_triggers: ["reconnaissance", "git_forensics", "churn", "hotspots", "bus_factor"]
---

# Codebase Reconnaissance: Git Forensics Protocol

Before diving into the source code, use these Git forensics to identify hotspots, risks, and institutional knowledge gaps. These commands help build a mental map of "danger zones" and key contributors.

## 1. Identify Churn (The "Danger Zones")
**Goal:** Find the 20 most-frequently changed files in the last year. High churn indicates active development or a "God Object."
```bash
git log --format=format: --name-only --since="1 year ago" | sort | uniq -c | sort -nr | head -20
```
**Interpretation:** If the top files are also technical debt items, they are major drivers of "codebase drag."

## 2. Evaluate the "Bus Factor"
**Goal:** Identify who built the system and check if they are still active.
- **Overall Contributors**: `git shortlog -sn --no-merges`
- **Active Contributors (Last 6 Months)**: `git shortlog -sn --no-merges --since="6 months ago"`
**Interpretation:** If one person has >60% of commits, the Bus Factor is high. If top contributors are absent from the 6-month list, knowledge has left the building.

## 3. Locate Bug Hotspots
**Goal:** Find where "fixes" are concentrated. Files constantly being fixed are likely fragile.
```bash
git log --format=format: --name-only --grep="fix\|bug\|broken" | sort | uniq -c | sort -nr | head -20
```
**Interpretation:** Cross-reference this with the Churn list. A file that is both high-churn and high-bug is a primary stability risk.

## 4. Gauge Project Velocity
**Goal:** Determine if the project is accelerating, stable, or dying by looking at yearly commit volume.
```bash
git log --date=format:"%Y-%m" --format="%ad" | sort | uniq -c
```
**Interpretation:** A steady decline may indicate maintenance mode. Sudden spikes followed by silence may suggest high-pressure firefighting.

## 5. Detect Crisis Patterns (Firefighting)
**Goal:** Find how often the team has to revert or hotfix.
```bash
git log --oneline --since="1 year ago" --grep="revert\|hotfix\|emergency\|rollback"
```
**Interpretation:** A long list suggests skipping QA or immense pressure to deploy, leading to a "patch-on-a-patch" culture.

## Usage Guidelines
- **Merge Strategy**: If the team uses Squash Merges, authorship reflects the merger rather than the individual authors. Verify the merge strategy first.
- **Context**: Use these commands as a "first-look" before running static analysis or deep-dive code reviews.