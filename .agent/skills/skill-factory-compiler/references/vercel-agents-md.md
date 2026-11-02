# Reference: AGENTS.md outperforms skills in our agent evals

**Source:** Jude Gao, Vercel Blog (Jan 27, 2026)
**URL:** https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals

## Key Findings
- **Passive Context > Active Retrieval:** AGENTS.md compressed index 100%; skill with explicit instructions 79%; skill default and no-docs baseline both 53% (skill never invoked). Scope: Next.js 16 APIs absent from model training data, one vendor, one framework (fetched 2026-11-01). Independent benchmarks (SkillsBench) find curated skills help, so treat this as evidence about invocation, not about skill content.
- **Decision Fatigue:** Agents often fail to invoke skills when they have to "decide" to use them.
- **Retrieval-Led Reasoning:** Explicitly telling agents to prefer retrieval-led reasoning over pre-training-led reasoning is crucial.
- **Compression:** A compressed 8KB docs index (pipe-delimited) embedded in AGENTS.md provides the "World Map" without bloating context.

## Compressed Index Format
Example:
```
[Docs Index]|root: ./.docs
|IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning
|path/to/dir:{file1.md,file2.md,...}
```

## Recommended Setup
1. Detect version.
2. Download/Locate documentation.
3. Inject compressed index into `AGENTS.md`.
