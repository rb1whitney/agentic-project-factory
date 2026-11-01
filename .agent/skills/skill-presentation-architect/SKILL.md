---
name: skill-presentation-architect
description: Narrative-first presentation architect. Builds consulting-grade decks (Big Idea, audience persona, storyline, evidence ledger, storyboard, editable PPTX) from technical, architecture, incident, or strategy material, including this repo's docs/ Skill-as-Pseudocode (SaP) architecture. Use when asked to create, storyboard, redesign, or audit a presentation.
---
# Skill: Narrative-First Presentation Architect (`skill-presentation-architect`)

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
<!-- SAP_BUNDLE_END -->

## Operating Contract & Stage Gate

Execute narrative-first presentation architecture, storyboard validation (`storyboard_path`, `narrative_brief_path`), and editable PPTX slide generation (`output_pptx`) from technical docs to produce `storyboard_status` and `deck_artifact_path`.

```text
INPUT -> DISCOVER -> NARRATIVE BRIEF -> HOSTILE EVIDENCE REVIEW -> STORYLINE -> STORYBOARD
  -> [HARD STOP: PAUSE FOR USER APPROVAL]
  -> SLIDE SPEC -> RENDER EDITABLE PPTX -> VISUAL QA -> FINAL PPTX
```

- **Governing Principle**: Design the strongest verifiable argument for the target audience first (`references/narrative-craft.md`), then use slides (`references/slide-patterns.md`, `references/visual-grammar.md`) to make that argument effortless to understand, believe, and act on.
- **Hard Approval Gate**: Stop after generating and validating `narrative-brief.yaml` and `storyboard.yaml`. Never render `.pptx` until the user approves the storyboard (unless explicitly instructed to run end-to-end).

## Hard Rules & Factory Integration

1. **Voice Separation**: Chat responses to the user MUST use `caveman-prose` (`Location | Problem | Fix`). Slide headlines, speaker notes, and narrative briefs MUST use complete, persuasive sentences. Never leak `caveman-prose` into slide text.
2. **Zero Emoji**: Never use emojis in chat, narrative briefs, storyboards, slide text, or speaker notes. Use typography and color tokens (`references/design-tokens.md`) for emphasis.
3. **Evidence Boundary & Hostile Review**: Every quantitative or architectural claim in `narrative-brief.yaml` and `storyboard.yaml` must bind to an `evidence_id` with file path + line/section (`references/evidence-and-claims.md`). Distinguish repo-measured numbers from external paper-reported benchmarks (`references/sap-docs-bridge.md`).
4. **One Idea Per Slide & Action Titles**: Every content slide requires a full-sentence conclusion headline (`<= 14 words`), `<= 4` visual chunks, and explicit layout pattern selection (`references/slide-patterns.md`).
5. **Deterministic Validation Before Delivery**: Run `scripts/validate_storyboard.py` on both `--brief` and storyboard YAML before presenting to the user, and complete the visual QA checklist (`references/quality-assurance.md`) before final PPTX hand-off.

## Reference, Schema & Script Routing Index

| Stage / Need | Purpose | File (`{SKILL_DIR}/`) |
| :--- | :--- | :--- |
| **Validator CLI** | Deterministic schema, headline-length, density, and evidence-binding checks | `scripts/validate_storyboard.py` |
| **Stage 1-4: Narrative Craft** | Audience persona, Big Idea (`point` + `stakes`), SCQA/Sparkline arcs, takeaway hierarchy | `references/narrative-craft.md`, `schemas/narrative-brief.md` |
| **Stage 3: Evidence Ledger** | Claim classification, source anchoring, hostile reviewer test | `references/evidence-and-claims.md` |
| **Repo SaP Architecture Decks** | Explaining `docs/SKILL_AS_PSEUDOCODE_ARCHITECTURE.md` to exec, architect, or onboarding audiences | `references/sap-docs-bridge.md`, `examples/architecture-decision.md` |
| **Stage 5: Storyboard & Patterns** | Pattern catalog (comparison, pipeline, 2x2, callout, chart, table) & anti-patterns | `references/slide-patterns.md`, `schemas/storyboard.md` |
| **Stage 6-7: Visual Grammar & Tokens** | Reading gravity, contrast, 16:9 spatial grid, typography & 60-30-10 color palette | `references/visual-grammar.md`, `references/design-tokens.md`, `schemas/slide-spec.md` |
| **Stage 8: Quality Assurance** | Pre-render storyboard gate and post-render visual inspection checklist | `references/quality-assurance.md` |
