# Evidence and Claims

## Claim status

Every material claim is one of:

- SOURCED
- DERIVED
- UNKNOWN
- CONFLICTED

## Sourced

Use when the exact fact is explicitly supported by provided source material or a verified external source.

Keep terminology faithful to the source unless the user asks for transformation.

## Derived

Use only when inputs are sourced.

Display arithmetic for material business-case calculations.

Example:
`600 × 2 hrs/week × $100/hr × 46 weeks = $5.52M/year`

Do not hide important assumptions inside a rounded result.

## Unknown

Use explicit brackets.

Examples:
- `[$__ / year]`
- `[__ hrs/week]`
- `[verify: config path]`
- `[owner]`

Do not convert unknowns into estimates without permission.

## Conflicted

If sources disagree:
- preserve the disagreement;
- identify the sources;
- explain what decision depends on it;
- do not silently reconcile.

## Technical claims

Treat file paths, configuration syntax, API behavior, permission models, version compatibility, and architecture behavior as facts requiring support.

"Probably true" is not a source.

## Recommendation logic

Separate:
- fact;
- inference;
- recommendation;
- assumption.

A recommendation can be strong while still acknowledging uncertainty.

## Evidence ledger

Recommended schema:

| ID | Claim | Status | Source | Arithmetic / reasoning | Slide |
|---|---|---|---|---|---|
| E1 | ... | SOURCED | ... | — | 2 |
| E2 | ... | DERIVED | E1 + E3 | ... | 2 |
| E3 | ... | UNKNOWN | — | — | 2 |

## Hostile review questions

- What number would an executive challenge first?
- Which technical statement could be stale?
- Which causal statement is actually only correlation?
- Which assumption is carrying the recommendation?
- What evidence would change the recommendation?
