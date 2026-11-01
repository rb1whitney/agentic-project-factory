# Visual Grammar

## Core rule

A visual must make the claim easier to understand than prose alone.

## Visual thesis

Every slide must state what the audience should see.

Examples:
- "Three inputs converge on one policy layer."
- "Cost of inaction grows with each additional harness."
- "The protocol boundary leaves client policy untouched."

## Mapping claims to forms

| Claim type | Preferred visual |
|---|---|
| Causal relationship | Flow |
| Architecture | System diagram |
| Transformation | Before / after |
| Quantitative relationship | Equation / chart |
| Options | Tradeoff matrix |
| Delivery | Roadmap |
| Failure | Broken loop / failure gate |
| Hierarchy | Nested structure |
| Single critical fact | Hero metric |
| Technical translation | Source → compiler → targets |
| Dense reference | Table / appendix |

## Visual hierarchy

One dominant claim.
One dominant visual.
Secondary evidence supports it.

Avoid:
- ornamental boxes;
- repeated cards;
- diagrams that merely restate bullet lists;
- tiny labels;
- unexplained icons;
- stock imagery without narrative function.

## Diagram rules

Use explicit semantics:
- blue = primary flow;
- green = validated target / desired outcome;
- coral = broken path / risk / unverified;
- dark slate = neutral system boundary.

Prefer native PowerPoint shapes or SVG for production. Use Mermaid as an intermediate description when useful, not as a mandatory renderer.

## Composition

Default:
- 60px safe margin;
- strong title zone;
- asymmetric composition when useful;
- generous whitespace;
- 75%+ purposeful frame utilization.

Do not fill space merely to satisfy a density target.
