#!/usr/bin/env python3
"""
compile_metadata.py - Recompile centralized agent and skill metadata catalogs.
Reads exclusively from standard canonical source locations (.agent/agents, .agent/skills)
where .agent/agents contains universal multi-adapter YAML specifications.
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def parse_frontmatter(file_path: Path) -> dict:
    """Fast regex parser for YAML frontmatter without external dependencies."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return {}

    match = re.match(r"^---\s*\n(.*?)\n---\s*(\n|$)", content, re.DOTALL)
    if not match:
        return {}

    frontmatter_text = match.group(1)
    metadata = {}

    for line in frontmatter_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val.startswith("[") and val.endswith("]"):
                items = [x.strip().strip('"').strip("'") for x in val[1:-1].split(",") if x.strip()]
                metadata[key] = items
            else:
                metadata[key] = val
    return metadata

def compile_agents(agents_dir: Path) -> list[dict]:
    """Scan canonical multi-adapter YAML agent specifications in .agent/agents."""
    agents = []
    if not agents_dir.exists():
        return agents

    for file_path in sorted(agents_dir.glob("*.yaml")):
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        # Read first YAML document up to ---
        parts = content.split("\n---")
        header = parts[0]
        meta = {}
        for line in header.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"').strip("'")

        agents.append({
            "name": meta.get("name", file_path.stem),
            "description": meta.get("description", ""),
            "version": meta.get("version", "1.0"),
            "source_file": str(file_path.relative_to(agents_dir.parent.parent))
        })
    return agents

def compile_skills(skills_dir: Path) -> list[dict]:
    """Scan standard skills directory in .agent/skills."""
    skills = []
    if not skills_dir.exists():
        return skills

    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir() or skill_path.name.startswith("."):
            continue
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            continue

        meta = parse_frontmatter(skill_md)
        name = meta.get("name", skill_path.name)
        desc = meta.get("description", "")
        ref_dir = skill_path / "references"
        ref_count = len(list(ref_dir.glob("*.md"))) if ref_dir.is_dir() else 0

        skills.append({
            "name": name,
            "description": desc,
            "path": str(skill_path.relative_to(skills_dir.parent.parent)),
            "references_count": ref_count
        })
    return skills

def main():
    parser = argparse.ArgumentParser(description="Compile agent and skill metadata index")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--output", default=".agent/metadata.json", help="Output compiled metadata path")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    agents_dir = root / ".agent/agents"
    skills_dir = root / ".agent/skills"
    output_file = root / args.output

    catalog = {
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "standard_locations": {
            "agents": ".agent/agents",
            "skills": ".agent/skills"
        },
        "agents": compile_agents(agents_dir),
        "skills": compile_skills(skills_dir)
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    print(f"Compiled metadata: {len(catalog['agents'])} agents, {len(catalog['skills'])} skills -> {args.output}")

if __name__ == "__main__":
    main()
