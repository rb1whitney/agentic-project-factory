# SaP Docs Bridge: Turning docs/ Pseudocode Architecture Into a Deck

Use when the deck source is this repo's `docs/` architecture set (Skill-as-Pseudocode, skills, contracts, hydration, conductor). The docs are the evidence base; the deck argues from them without restating all of them.

## Source map (read headings first, sections on demand)

| Topic | File | Use for |
| :--- | :--- | :--- |
| SaP law, ablation table, 5 lessons, 4-tier taxonomy, contracts vs skills, consolidation ledger, compiler pipeline | `docs/SKILL_AS_PSEUDOCODE_ARCHITECTURE.md` | Core argument |
| Skills model | `docs/skills-architecture.md` | Audience primer |
| Compile projection | `docs/ephemeral-projection-compiler.md` | Source -> compiler -> targets visual |
| Lifecycle | `docs/conductor-cdd-workflow.md` | Phase / roadmap slide |
| AST layer | `docs/ast-code-map-architecture.md` | Blast-radius slide |
| Factory overview | `docs/agentic-factory-architecture.md`, `docs/repository-architecture.md` | Context slide |

Retrieval: `grep -n '^#' <file> | bin/rtk` then read target sections only. Cite as `file#heading`.

## Candidate Big Ideas (pick by audience; do not mix)

- Engineering leads: "Replacing skill prose with a three-block pseudocode bundle (templates, skeleton, contracts) lets agents execute first try instead of re-retrieving, and a contract alone makes things worse."
- Platform owners: "Keeping child contracts out of the top-level skill pool avoids the flat-pool penalty the paper measured, while compile-time YAML keeps one source of truth for every consumer."
- Executives: "55 skills collapsed to 13 parents with zero asset loss; the remaining risk is [verify: production-task win rate, not yet measured here]."

## Claim ledger seed (statuses pre-set; re-verify against file before use)

| Claim | Status | Source anchor |
| :--- | :--- | :--- |
| Full bundle 30/134 wins vs raw prose 16/134 (+87.5%) on ALFWorld | SOURCED (paper, reported in docs section 1) | `SKILL_AS_PSEUDOCODE_ARCHITECTURE.md` section 1 table |
| Contract-only 13/134 (-18.8%) | SOURCED (paper) | same table |
| Flat pool 30 -> 22 wins (-27%) | SOURCED (paper, section 3.5 / 5.6 cited by docs) | section 3.1 item 2 |
| 55 skills -> 13 parents, -76.4% top-level noise | SOURCED (repo ledger) | section 4 |
| 87 scripts and 189 runbooks migrated | SOURCED (repo ledger) | section 4 |
| Verifier 0.0% false-positive promotion at (0.65, 0.35) on 30 synthetic controls | SOURCED (repo calibration); synthetic, not production | section 5 item 5 |
| This repo's agents win more on real tasks | UNKNOWN | no measurement in docs; bracket it |

Paper results are about ALFWorld. Never present them as measured on this repo. Label the evidence boundary on the slide: "Paper-reported, ALFWorld, n=134".

## Diagram-centric spine (recommended structure)

The docs' own diagram is the spine: `Source (contracts/*.yaml) -> SaP Compiler + 4-check verifier -> Runtime bundles (SKILL.md, agents/*.yaml)`. Use structure = Diagram-centric, with an Explainer wrapper for audiences new to SaP.

| Beat | Assertion title (example) | Pattern |
| :--- | :--- | :--- |
| 1 | Prose skills make agents re-retrieve and still guess the command. | FULL-CANVAS CLAIM |
| 2 | A typed contract alone scores below raw prose; it needs concrete templates beside it. | HERO METRIC (13 vs 16 vs 30) |
| 3 | Every skill ships three blocks: templates first, skeleton second, contracts third. | BEFORE / AFTER CODE & DIRECTORY |
| 4 | Contracts compile into skills and agents; the LLM never reads the YAML. | ASYMMETRIC ARCHITECTURE FLOW / DIAGRAM SPINE |
| 5 | Surfacing child contracts as top-level skills cost 27% in the paper, so the repo forbids it. | COMPARISON / TRADEOFF |
| 6 | Four tiers decide where a capability lives. | DIAGRAM SPINE (decision tree from section 3 mermaid) |
| 7 | Four deterministic checks gate promotion; destructive sinks hard-reject. | FAILURE & VALIDATION GATE |
| 8 | 55 skills became 13 with no asset lost; [production win-rate unmeasured]. | PHASED ROADMAP & DECISION |

Objection map: "Is this just prompt compression?" -> length-matched prose 18 vs bundle 30 (structural, not brevity). "Why a separate contracts folder?" -> three compile-time roles (DRY reuse, CI schema gate, non-circular verifier). "Does it generalize?" -> UNKNOWN beyond ALFWorld; state it.

## Visual rules specific to pseudocode decks

- Show real `## 1. Action Templates` snippets in code blocks at 20px minimum; truncate to 4-6 lines, label `...` explicitly.
- `invoke(...)` is notation, not a binary: any slide showing it carries the line "invoke(...) is pseudocode notation, not a shell command".
- Mermaid from docs may be re-drawn as native shapes; keep node labels verbatim.
- Coral = unverified or rejected path (contract-only, flat pool). Blue = flow. Green = promoted/verified.
- Reference the compiler pipeline commands only from `docs/` section 5; do not invent flags.

## Hand-off

After storyboard approval, USER tags `@swarm-engineer` for render. Narrative-only requests stop at the storyboard.
