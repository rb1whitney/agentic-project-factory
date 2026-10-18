---
pack_id: wa-pack-python-sus
language: python
pillar: SUS
rule_count: 6
rules:
- id: wa-py-sus-wildcard-import
  pillar: SUS
  severity: MEDIUM
  language: python
  problem: Wildcard `from module import *` pollutes namespace and breaks static dependency
    analysis.
  fix: Import explicit symbols (`from module import sym1, sym2`).
  rule:
    kind: wildcard_import
- id: wa-py-sus-global-stmt
  pillar: SUS
  severity: MEDIUM
  language: python
  problem: Mutating module-level state via `global` couples functions and breaks thread
    safety.
  fix: Pass state explicitly or encapsulate in a class.
  rule:
    kind: global_statement
- id: wa-py-sus-nested-for-3
  pillar: SUS
  severity: MEDIUM
  language: python
  problem: Triply nested `for` loop (O(N^3)) degrades readability and CPU sustainability.
  fix: Pre-index inner collections into a `dict` or `set` for O(1) lookup.
  rule:
    kind: for_statement
    inside:
      kind: for_statement
      inside:
        kind: for_statement
        stopBy: end
      stopBy: end
- id: wa-py-sus-exec-compile
  pillar: SUS
  severity: MEDIUM
  language: python
  problem: Runtime `compile()` obscures call graphs and static type checking.
  fix: Use standard functions or dataclasses.
  rule:
    pattern: compile($SRC, $$$ARGS)
- id: wa-py-sus-locals-mutation
  pillar: SUS
  severity: LOW
  language: python
  problem: Accessing `locals()` dynamically harms readability and JIT/static analysis.
  fix: Use an explicit dictionary.
  rule:
    pattern: locals()[$$$ARGS]
- id: sg-python-useless-if-body
  pillar: SUS
  severity: MEDIUM
  language: python
  problem: Useless if statement; both blocks have the same body
  fix: https://docs.python.org/3/tutorial/controlflow.html
  rule:
    pattern: "if $X:\n    $S\nelse:\n    $S"
---

# Well-Architected Policy Pack: PYTHON — SUS

Contains **6** verified `ast-grep` structural policies for `python` mapped to the **SUS** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-py-sus-wildcard-import` | `MEDIUM` | Wildcard `from module import *` pollutes namespace and breaks static dependency analysis. | Import explicit symbols (`from module import sym1, sym2`). |
| `wa-py-sus-global-stmt` | `MEDIUM` | Mutating module-level state via `global` couples functions and breaks thread safety. | Pass state explicitly or encapsulate in a class. |
| `wa-py-sus-nested-for-3` | `MEDIUM` | Triply nested `for` loop (O(N^3)) degrades readability and CPU sustainability. | Pre-index inner collections into a `dict` or `set` for O(1) lookup. |
| `wa-py-sus-exec-compile` | `MEDIUM` | Runtime `compile()` obscures call graphs and static type checking. | Use standard functions or dataclasses. |
| `wa-py-sus-locals-mutation` | `LOW` | Accessing `locals()` dynamically harms readability and JIT/static analysis. | Use an explicit dictionary. |
| `sg-python-useless-if-body` | `MEDIUM` | Useless if statement; both blocks have the same body | https://docs.python.org/3/tutorial/controlflow.html |
