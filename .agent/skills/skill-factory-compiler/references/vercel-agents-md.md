# Reference: AGENTS.md outperforms skills in our agent evals

**Source:** Jude Gao, Vercel Blog (Jan 27, 2026)
**URL:** (Hypothetical) https://vercel.com/blog/agents-md-outperforms-skills

## Key Findings
- **Passive Context > Active Retrieval:** AGENTS.md achieved 100% pass rate in Next.js 16 evals, while skills maxed out at 79% with explicit instructions.
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
