# Example: Architecture Decision

## Input

A platform team has three AI coding harnesses. Each expects different project instructions, MCP configuration, and permission controls. Developers manually reproduce configuration across repositories.

The proposal is a single declarative manifest compiled into each harness's native format.

## Narrative Brief

### Big Idea

> One declarative developer-intent layer can preserve harness choice without making every developer maintain three configuration dialects.

### Stakes

If fragmentation continues, configuration effort and drift grow with every supported harness; if the team builds an adapter, developers keep tool choice while the platform team owns translation.

### Audience

Platform leadership and staff engineers deciding whether to fund a small platform investment.

### Takeaways

1. The fragmentation is real because the harnesses standardize different layers.
2. MCP does not eliminate client-side configuration policy.
3. A compiler / adapter can centralize intent while preserving native configs.

### Story structure

Pitch:
- current state;
- configuration tax;
- why the obvious standard does not solve it;
- proposed adapter;
- alternatives;
- rollout;
- decision.

### Strong objections

- "Why not standardize on one harness?"
- "Isn't MCP supposed to solve this?"
- "Who maintains the adapter when vendors change formats?"
- "Is the configuration tax actually large enough to justify $150K?"

## Ghost Deck

1. Three AI harnesses force 600 developers to maintain the same intent in different dialects.
2. The annual configuration tax should be compared directly with the $150K cost to fix it.
3. MCP standardizes server communication but leaves client configuration policy fragmented.
4. One declarative manifest can compile shared intent into each harness's native configuration.
5. CI can catch vendor format changes before they reach developers.
6. A phased rollout limits risk while preserving developer choice.
7. The decision is whether to fund the adapter or accept continuing fragmentation.
