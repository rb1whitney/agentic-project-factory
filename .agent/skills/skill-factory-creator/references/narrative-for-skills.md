# Narrative for Skills (Moghe / Fowler method applied to skill design)

Source method: Sumeet Gayathri Moghe, "Nail your narrative", martinfowler.com/articles/never-send-slides/nail-your-narrative.html. Full method: `.agent/skills/skill-presentation-architect/references/narrative-craft.md`.

Claim: a skill is a short talk delivered to an agent. Decide the argument before the format. This is an analogy used as a design checklist, not a claim the article is about skills.

## Mapping

| Moghe step | Skill-design equivalent | Artifact |
| :--- | :--- | :--- |
| Big Idea = point of view + stakes | Trigger + what breaks without it ("Triage K8s pods before mutating; otherwise remediation runs out of order") | `description` frontmatter, contract `trigger` |
| Audience persona (name, knowledge, goals, why care, <=3 takeaways) | Consuming agent: which `.agent/agents/*` binds it, what tools it has, what it already knows, <=3 outputs it must return | `source_parents`, agent `skills:`, `output_schema` |
| Situation changes the talk (Zoom decision vs keynote) | Interactive agent (asks USER) vs autonomous subagent (no questions) | preconditions, approval gates |
| Pick a story structure | Pick the procedure shape: linear pipeline, gate-then-act, diagnose-branch-fix, fan-out/collect | Block 2 skeleton |
| Voice it without slides | Block 1 alone must let an agent act correctly | Action Templates |
| Storyboard (one note per slide, no polish) | Skeleton steps (one line per step, no prose) | Block 2 |
| Slides come last | Reference runbooks and scripts come last | Tier 3/4 |
| Iterate; design may reopen narrative | If templates cannot express the step, revisit the trigger or the tier | Q1-Q4 re-run |
| Learn the rules, then break them | Compress for small Tier 4 additions; full sequence for new Tier 1 | creator workflow |

## Procedure

1. Write the Big Idea for the skill as one speakable sentence: `<agent> uses <skill> to <outcome>; without it <failure>`.
2. Write the persona line: bound agent, tools, prior knowledge, <=3 return values.
3. Choose procedure shape and justify in one line.
4. Voice test: could the agent do the job from Block 1 only? If not, add the missing concrete command.
5. Only then run `taxonomy-decision.md` for placement and write bundle blocks.

## Rejection from the narrative step

- Big Idea reads as a topic label ("AWS stuff"). Reject, rewrite as claim + stakes.
- No bound agent can be named. Reject (orphan).
- More than 3 outputs. Split or trim.
