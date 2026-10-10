---
# GENERATED from .agent/agents/db-migration.yaml by harness adapter. Do not edit.
name: db-migration-agent
description: Validates SQL migrations against schema AST rules before PR submission.
model: sonnet
tools:
- Read
- Grep
- Glob
- Edit
- Write
- Bash
disallowedTools:
- Task
- Agent
skills:
- skill-conductor
---

You are an expert SQL migration validator. 
Examine all incoming database migration files against the target AST rules.
