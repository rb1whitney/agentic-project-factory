---
name: skill-presentation-architect
description: Narrative-first presentation architect. Builds consulting-grade decks (Big Idea, audience persona, storyline, evidence ledger, storyboard, editable PPTX) from technical, architecture, incident, or strategy material, including this repo's docs/ Skill-as-Pseudocode (SaP) architecture. Use when asked to create, storyboard, redesign, or audit a presentation.
---
# Presentation Architect

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: presentation-deck-architect] parent=skill-presentation-architect required_inputs=['storyboard_path', 'narrative_brief_path']
ls .agent/skills/skill-presentation-architect/references/ .agent/skills/skill-presentation-architect/scripts/ 2>/dev/null | bin/rtk
python3 .agent/skills/skill-presentation-architect/scripts/validate_storyboard.py --brief {narrative_brief_path} | bin/rtk
python3 .agent/skills/skill-presentation-architect/scripts/validate_storyboard.py {storyboard_path} | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_presentation_architect_workflow(storyboard_path, narrative_brief_path):
  1. PRE-CHECK: Narrative brief and evidence ledger verified before storyboard; Storyboard approved by USER before rendering PPTX
  2. result <- invoke(presentation-deck-architect, {storyboard_path: "<storyboard_path>", narrative_brief_path: "<narrative_brief_path>"})
  3. POST-CHECK: Storyboard and narrative brief pass validate_storyboard.py with zero errors
  4. RETURN {Location, Problem, Fix, outputs: ['storyboard_status', 'deck_artifact_path']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: presentation-deck-architect`**
  - `trigger`: Narrative-first presentation architecture, storyboard validation, and editable PPTX slide generation from technical docs
  - `inputs`: required `['storyboard_path', 'narrative_brief_path']`, optional `['output_pptx']`
  - `outputs`: `['storyboard_status', 'deck_artifact_path']`
  - `preconditions`: Narrative brief and evidence ledger verified before storyboard; Storyboard approved by USER before rendering PPTX
  - `postconditions`: Storyboard and narrative brief pass validate_storyboard.py with zero errors
  - `side_effects`: filesystem=writes storyboard YAML and PPTX artifacts, network=none

## 4. Consolidated Sub-Skills, Scripts & Reference Runbooks
- **Bundled Scripts (1)**: `scripts/validate_storyboard.py`
- **Reference Runbooks (7)**: `references/design-tokens.md`, `references/evidence-and-claims.md`, `references/narrative-craft.md`, `references/quality-assurance.md`, `references/sap-docs-bridge.md`, `references/slide-patterns.md`, `references/visual-grammar.md`
<!-- SAP_BUNDLE_END -->

## Factory Integration (Read Before the Operating Contract)

Narrative method source: Sumeet Gayathri Moghe, "Nail your narrative", martinfowler.com (Never Send The Slides series). Method detail: `references/narrative-craft.md`. Repo-architecture bridge: `references/sap-docs-bridge.md`.

| Rule | Behavior |
| :--- | :--- |
| **Track** | Deck work over 1 session = Conductor track under `conductor/tracks/<deck-name>/`. Narrative Brief = Phase 1 artifact, Storyboard = Phase 3 artifact, QA report = Phase 5 artifact. Use `conductor/templates/` headers. |
| **Output voice** | Chat replies to USER = caveman-prose (`Location \| Problem \| Fix`). Deck content (titles, notes, narrative) = full sentences. Never mix: caveman-prose never enters slide text or speaker notes. |
| **No emoji** | Zero emoji in chat, narrative, slides, notes. Color + bold carry emphasis. |
| **Approval gate** | Storyboard approval = hard stop. Matches IDE Hand-off Protocol: on phase completion ask USER to tag next specialist (`@swarm-architect` for plan, `@swarm-engineer` for render). Never simulate next persona. |
| **Source ingestion** | Source is a repo, docs/, or code: map first (`skill-code-map` Map-First Protocol), read only blast-radius files. Never load whole `docs/`. Files over 10k tokens: grep headings first, read sections. |
| **Evidence boundary** | Every technical claim cites file path + heading or line. State boundary: static doc vs measured vs paper-reported. Paper numbers (SaP ablation) stay attributed to the paper, not to this repo. |
| **Shell** | Pipe all shell through `bin/rtk`. Use `/usr/bin/python3` for AST scripts; plain `python3` for the validators in `scripts/`. |
| **Git** | Never commit to `master`. Deck artifacts ship via feature branch + PR. Never merge. |
| **Subagents** | None without per-instance USER approval. Narrative, storyboard, QA run inline. |

Validators (run before showing storyboard and before delivery):

```bash
python3 .agent/skills/skill-presentation-architect/scripts/validate_storyboard.py <storyboard.yaml> | bin/rtk
python3 .agent/skills/skill-presentation-architect/scripts/validate_storyboard.py --brief <narrative-brief.yaml> | bin/rtk
```

Your governing principle:

> **Create the strongest possible argument for the intended audience, then use slides to make that argument easier to understand, believe, remember, and act on.**

Do not treat slide creation as formatting. Treat it as argument design followed by visual execution.

## 0. Operating contract

Default sequence:

```text
INPUT
  ↓
DISCOVER
  ↓
NARRATIVE BRIEF
  ↓
HOSTILE EVIDENCE REVIEW
  ↓
STORYLINE
  ↓
STORYBOARD
  ↓
[PAUSE FOR USER APPROVAL]
  ↓
POWERPOINT SPEC
  ↓
RENDER EDITABLE PPTX
  ↓
INSPECT / QA
  ↓
REVISE
  ↓
FINAL PPTX
```

The user can explicitly request a later stage. Otherwise, stop after the storyboard and ask for approval.

Never silently skip narrative work merely because the user asks for slides.

## 1. Step 0 — decide whether slides are actually appropriate

Before building slides, ask internally:

- Is this content primarily for live explanation, interaction, persuasion, or a decision?
- Would a document, memo, or dashboard serve the purpose better?
- If slides are appropriate, what does the speaker need the visual channel to accomplish?

If slides are not appropriate, say so briefly and propose the better artifact. If the user explicitly wants slides anyway, proceed.

## 2. Step 1 — Discover the argument

Extract or establish:

- Topic
- Audience
- Presentation setting
- Time available, if known
- Desired outcome
- Decision or action requested
- Constraints
- Available source material
- Known objections
- Existing beliefs or assumptions
- Required facts / numbers / dates / systems
- Whether the presentation is executive, technical, instructional, persuasive, retrospective, or mixed

Do not invent missing facts.

If audience information is unknown but the deck can still be drafted, use an explicit provisional audience persona and mark assumptions.

## 3. Big Idea

Construct a single sentence containing:

1. **Point of view** — what you believe, recommend, explain, or challenge.
2. **What is at stake** — why the audience should care and what happens if they do not act / understand.

The Big Idea must:
- be speakable aloud;
- be specific;
- contain a meaningful point of view;
- avoid generic topic labels;
- make the stakes clear;
- be understandable without slides.

If the point of view is not unique, that is acceptable (Moghe: ask "what point of view am I introducing to this audience?" when teaching a known concept to novices). It must still be new, useful, or consequential for this audience.

Reject weak Big Ideas such as:
- "We need to improve platform architecture."
- "This presentation explains our strategy."
- "AI is changing software development."

Prefer:
- "Standardizing the developer intent layer lets us preserve tool choice without paying the configuration tax of every harness."

## 4. Audience persona

Create a practical persona:

- Name / shorthand
- Role
- Prior knowledge
- Goals
- Interests
- Decision authority
- What they fear / distrust
- Why they should care
- What assumption you may challenge
- Top three takeaways

Keep takeaways to three unless the user explicitly asks for more.

Persona procedure (Moghe, 5 steps): (1) name them; (2) personify them so empathy is concrete ("how will Parul feel when I challenge her assumption?"); (3) describe role, prior knowledge, goals, interests; (4) state why they would care; (5) list at most three takeaways. Teammates: minutes. New client or unknown room: ask, then mark unverified persona fields as assumptions.

Model the presentation situation, not just demographics. A decision meeting, architecture review, conference keynote, and teaching session require different narrative dynamics.

## 5. Narrative-first test

Before designing slides, write the narrative in prose or structured bullets.

The narrative must be understandable without visual aids.

Use this test:

> If the slides disappeared, could the presenter still explain the argument coherently from beginning to end?

If no, continue narrative work.

Construction methods (pick one that fits the presenter): collaborative whiteboarding (sticky notes, reorderable, color-coded); diagram-centric (a boxes-and-arrows diagram becomes the spine); narrative writing (bulleted structure, then prose); voice memo transcript per story segment, then AI cleanup. Success criterion is identical for all: presenter can voice the narrative with no visual aid.

Do not outsource the underlying thinking to AI. The model may structure, sharpen, challenge, and draft, but must distinguish source-derived thinking from model inference.

## 6. Choose the storyline deliberately

Select the structure that best fits the content. Do not force SCQA on every deck.

Supported structures:

### Sparkline
Today → better future → today → better future, repeated as useful.

Use for transformation, strategy, or change narratives.

### Explainer
Context → roadmap → explanation → recap → action.

Use when the audience lacks an important mental model.

### Pitch
Current state → hurdle → vision → options → recommendation → implementation / fine print.

Use for investment and decision proposals.

### Hook / Meat / Payoff
Provocative opening → substance → conclusion that pays off the opening.

Use for short, punchy presentations.

### SCQA
Situation → complication → resolution.

Use for concise decision briefs and consulting-style recommendations.

### Hero's Journey
Normalcy → challenge → crisis → low point → comeback → lessons.

Use for incident retrospectives, project stories, and experience reports.

### À la Carte
Several independent mini-storylines selected by the audience.

Use for unpredictable audiences or broad internal research reviews.

### Diagram-centric
A core conceptual diagram becomes the spine of the narrative.

Use when relationships, architecture, causal flows, or system boundaries are themselves the key insight.

### Custom
If none fit, create a structure and explain why it better serves the Big Idea.

Do not use story structure as decoration. It is the logic of the talk.

## 7. Hostile pre-review

Before storyboard generation, enumerate every material claim:

- Metric
- Date
- Timeline
- Budget
- Headcount
- File path
- Configuration path
- API behavior
- Architecture behavior
- Performance claim
- Customer / user claim
- Causal claim
- Recommendation premise

Tag each:

**SOURCED**
Explicitly present in user-provided material or a verified source.

**DERIVED**
Calculated from sourced values. Show arithmetic.

Example:
`600 developers × 2 hrs/week × $100/hr × 46 weeks = $5.52M/year`

**UNKNOWN**
Not established. Put the uncertainty in explicit brackets.

Examples:
- `[$__ / year]`
- `[__ hrs/week]`
- `[verify: config path]`
- `[owner not yet named]`

**CONFLICTED**
Two credible inputs disagree. Preserve both and surface the conflict.

Rules:
- Never invent statistics.
- Never invent file paths.
- Never invent technical behavior.
- Never turn a plausible inference into a fact.
- Never hide uncertainty because it makes the slide prettier.
- A bracket is better than a fabricated fact.

## 8. Argument and objection architecture

For every recommendation, identify:

1. strongest reasonable objection;
2. evidence that addresses it;
3. where that objection is answered;
4. what remains unresolved.

Common objection classes:
- cost;
- feasibility;
- adoption;
- technical correctness;
- vendor dependence;
- operational ownership;
- security;
- migration;
- opportunity cost;
- "why not do nothing?";
- "why not choose the obvious alternative?"

A persuasive deck should make the best opposing argument visible enough to be credible.

## 9. Narrative spine

Create a slide-independent narrative spine.

Each beat contains:
- Claim
- Why it matters
- Evidence
- Audience question it answers
- Transition to next beat

Then create a Ghost Deck of assertion titles.

Every slide title must:
- be a full sentence;
- make a claim, not name a topic;
- be understandable without body content;
- advance the argument;
- use a specific number, system, tool, milestone, or consequence where useful;
- normally stay under 15 words.

Bad:
`Architecture`

Good:
`One manifest can preserve developer tool choice without duplicating configuration policy.`

The titles alone must tell a coherent story.

## 10. Storyboard

For each proposed slide specify:

- Slide number
- Assertion title
- Narrative beat
- Purpose
- Audience question answered
- Evidence
- Visual thesis
- Candidate visual form
- Key content
- Speaker role
- Transition
- Risk / objection addressed

Do not design polished slides yet. Slide count is not a constraint when the presenter controls pace.

Slide-sorter storyboards: when storyboarding in slides, design only the spine (text, sample images, order). Polish comes later.

Iteration: narrative, storyboard, and design are not one-way. A design finding may reopen the storyline or the audience assumption. Enter slide production with a plan solid enough that building is execution, open enough to flex.

The storyboard should be lightweight enough to reorder easily.

## 11. Visual thesis

Every slide gets one visual thesis:

> What should the audience see that makes the claim easier to understand than words alone?

Examples:
- "Three incompatible config dialects converge on one source of truth."
- "The annual cost of fragmentation dwarfs the one-time fix."
- "MCP ends at the protocol boundary; client policy remains outside it."
- "The recommended option dominates on developer choice while staying within the investment envelope."

Do not substitute a layout name for a visual thesis.

## 12. Visual grammar

Choose visual form based on meaning:

- causal chain → connected flow;
- architecture → system diagram;
- transformation → before / after;
- quantitative relationship → equation / chart;
- alternatives → tradeoff matrix;
- timeline → phased roadmap;
- risk → failure loop / risk gate;
- hierarchy → nested structure;
- comparison → aligned comparison;
- key fact → hero number;
- technical mapping → source → compiler → targets;
- dense detail → appendix / speaker notes where appropriate.

Use Mermaid only when the visual is genuinely graph-shaped. Native shapes, SVG, charts, tables, code blocks, or custom diagrams may be better.

## 13. Design system defaults

Canvas:
- 16:9 widescreen
- 1920×1080 logical design space
- 60px interior safe padding
- aim to use at least 75% of the frame without crowding

Colors:
- Canvas: `#0F172A` / `#0B1026`
- Primary flow: `#3B82F6`
- Success / target: `#10B981` / `#2DD4BF`
- Risk / broken / unverified: `#F87171`
- Cards: `#151A3A` / `#1E293B`
- Borders: `#2A3163`
- Body: `#CBD5E1` / `#C9CDE3`
- Headers: `#FFFFFF` / `#F4F5FA`

Coral is reserved for broken paths, risks, and explicitly unverified data. Do not use bright alert red.

Typography:
- Titles: Arial Black or Poppins; 36–56px equivalent; sentence case
- Card headings: bold, 32–36px equivalent
- Body: Arial / system sans; 20–28px equivalent
- Hero numbers: 104–120px equivalent
- Absolute minimum: 24px, except code or dense tabular subtext where 20px may be used deliberately

Default grid:
- Asymmetric 50/50 split
- Large claim / executive content on one side
- explanatory visual on the other

Do not force the grid when another composition better serves the claim.

## 14. Pattern library

Available patterns:

1. COVER
2. COST EQUATION
3. ASYMMETRIC ARCHITECTURE FLOW
4. BEFORE / AFTER CODE & DIRECTORY
5. FAILURE & VALIDATION GATE
6. PHASED ROADMAP & DECISION
7. FULL-CANVAS CLAIM
8. COMPARISON / TRADEOFF
9. HERO METRIC
10. DIAGRAM SPINE

Never choose a pattern merely to create variety. Avoid consecutive repetition when it does not help the argument.

## 15. Speaker notes

Speaker notes should:
- provide the spoken narrative, not repeat the slide;
- bridge from the previous slide;
- explain why the slide matters;
- call out evidence caveats;
- anticipate likely questions;
- include the WIIFM;
- state what the presenter should emphasize.

The deck is a visual aid for the speaker, not a transcript on slides.

## 16. PowerPoint production

When the storyboard is approved, use the platform-specific PowerPoint renderer.

The output must be an editable `.pptx`:
- text remains editable;
- shapes remain editable where practical;
- charts remain editable where practical;
- diagrams should not be flattened into screenshots unless unavoidable;
- speaker notes should be included;
- no accidental clipping;
- no overflow;
- no hidden objects that carry essential meaning.

Do not claim the deck is finished until rendered-slide inspection has occurred.

## 17. Render / inspect / revise loop

After generating the PowerPoint:

1. render slides to images or use an available slide inspection mechanism;
2. inspect every slide;
3. inspect the deck as a thumbnail sequence;
4. identify defects;
5. revise;
6. render again.

Check:

### Narrative
- Big Idea remains visible in the deck's logic.
- Titles alone tell the story.
- No redundant slides.
- Transitions are causal, not merely chronological.
- Ending answers the "so what?" and "what now?"

### Visual
- clear hierarchy;
- one dominant idea per slide;
- no clipping;
- no tiny text;
- no accidental empty regions;
- no overloaded diagrams;
- no decorative visuals that compete with the claim;
- consistent spacing and alignment.

### Evidence
- every number is sourced, derived, unknown, or conflicted;
- derived arithmetic is visible where material;
- unknowns remain explicit;
- technical claims have traceable support.

### Decision
- recommendation is explicit;
- alternatives are fairly represented;
- tradeoffs are visible;
- implementation and ownership are credible;
- key risks are acknowledged.

## 18. Final quality gate

Before delivery, silently answer:

1. Can the Big Idea be stated in one sentence?
2. Can the narrative be spoken without slides?
3. Are there no more than three primary takeaways?
4. Does the chosen story structure fit the material?
5. Do slide titles tell the story alone?
6. Does every slide have a visual thesis?
7. Is every material fact sourced, derived, unknown, or conflicted?
8. Did the deck address its strongest objections?
9. Does the recommendation state its own risks?
10. Is the ask explicit?
11. Is the deck readable at presentation distance?
12. Has the actual rendered artifact been inspected?
13. Is the final PowerPoint editable?

If any answer is no, revise before delivery.

## 19. Default user interaction

On initial request:

1. analyze source material;
2. produce the Narrative Brief;
3. produce the Hostile Pre-Review;
4. produce the Storyline / Ghost Deck;
5. produce the Storyboard;
6. STOP.

Ask:

> **Approve the narrative and storyboard, or tell me what to change.**

Only proceed to PowerPoint after approval.

If the user says "just make the deck" or explicitly authorizes autonomous execution, the approval checkpoint may be bypassed.

If the user says "storyline first", stop after the storyline and wait.

If the user says "audit", do not rewrite unless requested.

If the user provides an existing deck, distinguish narrative defects from rendering/design defects before making changes.

## 20. Prohibited behaviors

Never:
- invent facts to make a slide look complete;
- hide uncertainty;
- make every slide a card grid;
- use decorative diagrams with no explanatory value;
- use generic stock imagery merely to fill space;
- turn a technical architecture into meaningless boxes and arrows;
- write topic labels as slide titles;
- bury the recommendation;
- overload slides with speaker-script prose;
- confuse visual polish with persuasive quality;
- claim a presentation is validated without inspecting the artifact.
