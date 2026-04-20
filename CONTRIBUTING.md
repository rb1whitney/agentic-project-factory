# Contributing to Programming-Work

This repository is a centralized hub for AI agents and skills across Claude, Copilot, and Gemini. Contributions should maintain the standards that make the system work  primarily that agents can reliably activate the right expertise for any task without being told to.

---

## Adding a New Skill

Skills live in `skills/<skill-name>/`. Each skill requires exactly two things:

### 1. `SKILL.md`

```markdown
---
name: my-skill-name
description: Dense trigger-keyword description. Include service names, error patterns, and scenarios. Example: Use for EKS pod failures, RBAC denials, CrashLoopBackOff, and ingress misconfigurations.
related_skills: ["@other-skill-name"]
auto_triggers: ["keyword1", "keyword2", "service_name"]
---
# Skill Title

## Mandatory on Activation
Upon activation you MUST immediately list and index the contents of the `references/` directory.
Read relevant runbooks before forming any diagnosis or recommendation.

## Core Expertise
...
```

**Description rules** (critical for activation accuracy):
- Include specific service names, not categories ("EC2, EBS, AutoScaling" not "AWS compute")
- Include common error patterns ("CrashLoopBackOff, ImagePullBackOff, OOMKilled")
- Include operational scenarios ("use for... when... if you see...")
- Minimum 2 sentences, maximum 5 sentences

### 2. `references/` (for expert skills)

Drop production runbooks into `references/` as Markdown files. Naming convention:

```
ServiceNameIssueType.md       # e.g. RDSConnectivityLoss.md
ComponentActionResult.md      # e.g. AutoScalingLaunchFailure.md
```

After adding a skill, update `skills/INVENTORY.md` by running:

```bash
python3 tools/update_inventory.py
```

---

## Adding a New Agent

Agents live in `agents/<agent-name>/`. An agent is a persona that auto-loads skills.

Create `agents/<agent-name>/AGENT.md` with:
- The agent's identity and scope
- Which skills to autoload using `@skill-name` references
- When to use this agent vs. activating skills directly

---

## Adding SRE Runbooks

Find the correct expert skill for the service affected:

| Service | Skill |
|---|---|
| EC2, EBS, AutoScaling | `skills/aws-ec2-expert/references/` |
| RDS, Aurora, DynamoDB | `skills/aws-rds-expert/references/` |
| VPC, Route53, ELB | `skills/aws-networking-expert/references/` |
| IAM, KMS | `skills/aws-iam-expert/references/` |
| Lambda, SQS, SNS | `skills/aws-serverless-expert/references/` |
| Kubernetes, EKS, GKE | `skills/kubernetes-expert/references/` |
| Multi-cloud automation | `skills/cloud-ops-expert/references/` |

Do not add runbooks to `cloud-debugger`  distribute them to the specific service expert.

---

## Modifying AGENT.md

`AGENT.md` is the passive context file injected into every agent session. It is symlinked as `CLAUDE.md`, `GEMINI.md`, and `.github/copilot-instructions.md`  edit only `AGENT.md`.

**Rules for AGENT.md edits**:
- The `IMPORTANT: Prefer retrieval-led reasoning...` directive must remain the first instruction
- The skills index must remain inline  do not replace it with a link to another file
- Every new skill must be added to the skills index in the correct category
- Descriptions in the index must match the trigger keywords in the skill's `SKILL.md`

See `docs/agent-md-design-rationale.md` for the research behind these constraints.

---

## Updating conductor/

The `conductor/` files define project-level context that agents read before architecture tasks.

| File | When to update |
|---|---|
| `tech-stack.md` | When adding a new approved technology or service |
| `product-guidelines.md` | When product vision or constraints change |
| `workflow.md` | When CI/CD or deployment process changes |
| `product.md` | When the product scope changes |

---

## AST Tools

After significant changes to source code in `tools/`, regenerate the code map:

```bash
python3 tools/ast-bridge/code_mapper.py .
```

The `code_map.md` and `.ast_cache/context_map.json` are in `.gitignore`  they are generated at runtime and not committed.

---

## PR Checklist

- [ ] Skill descriptions are trigger-dense (specific service names, error patterns)
- [ ] `SKILL.md` includes the Knowledge Bootstrap directive
- [ ] New runbooks are in the correct service expert's `references/` folder
- [ ] `skills/INVENTORY.md` is updated (`python3 tools/update_inventory.py`)
- [ ] `AGENT.md` skills index is updated if a new skill was added
- [ ] `conductor/tech-stack.md` is updated if a new tool was approved
- [ ] No secrets, credentials, or `.tfvars` files are committed