# Agentic Initializer (Vercel-Standard)




This skill automates the creation of a high-performance `AGENTS.md` manifest. Inspired by Vercel's research, it prioritizes "retrieval-led reasoning" over model pre-training by embedding a compressed documentation index directly into the repository root.

## Logic Overview
1. **Deterministic Scanning**: Scans a designated documentation directory (default: `docs/`) using `.agent/skills/skill-factory-compiler/scripts/scanner.py`.
2. **Compressed Indexing**: Builds a pipe-delimited 8KB "World Map" that maps paths to documentation files.
3. **Passive Context Delivery**: Generates an `AGENTS.md` that acts as the primary cognitive guide for LLM agents, ensuring they always have access to version-matched documentation.
4. **Retrieval-Led Reasoning**: Injects explicit instructions to prefer retrieval from local docs over potentially outdated training data.

## Usage
```bash
# Initialize a repository with Vercel-style AGENTS.md
python3 .agent/skills/skill-factory-compiler/scripts/logic.py <target_path> <project_name> [docs_dir]
```

## References
- See `.agent/skills/skill-factory-compiler/references/vercel-agents-md.md` for the original research findings by Jude Gao (Next.js/Vercel).
