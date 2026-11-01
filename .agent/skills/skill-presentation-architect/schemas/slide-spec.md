# Slide Specification Schema

```yaml
slide:
  number: 1
  title:
    text: ""
    assertion: true

  pattern: ""
  narrative:
    beat: ""
    purpose: ""
    transition: ""

  evidence:
    - id: ""
      status: "SOURCED|DERIVED|UNKNOWN|CONFLICTED"

  visual:
    thesis: ""
    form: ""
    layout: ""
    objects: []

  content:
    bluf: ""
    pillars: []
    labels: []
    tables: []
    charts: []
    code: []
    diagrams: []

  speaker_notes:
    bridge: ""
    emphasis: ""
    wiifm: ""
    caveats: ""
    likely_questions: []

  qa:
    overflow_risk: false
    readability_risk: false
    fact_risk: false
```
