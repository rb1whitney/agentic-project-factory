#!/usr/bin/env python3
"""
verify_runtime_discovery.py - Test script to verify loaded agents and skills
for Claude Code and Antigravity (agy) harnesses.
Checks projection directories, schema validity, frontmatter parsing,
and standard metadata synchronization.
"""

import json
import re
import sys
from pathlib import Path

def parse_yaml_frontmatter(content: str) -> dict:
    match = re.match(r"^---\s*\n(.*?)\n---\s*(\n|$)", content, re.DOTALL)
    if not match:
        return {}
    meta = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if v.startswith("[") and v.endswith("]"):
                meta[k] = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
            else:
                meta[k] = v
    return meta

def verify_claude_projection(repo_root: Path):
    claude_agents_dir = repo_root / ".claude/agents"
    if not claude_agents_dir.exists():
        return {"status": "FAIL", "error": f"Missing directory: {claude_agents_dir}", "agents": []}
    
    loaded_agents = []
    for file_path in sorted(claude_agents_dir.glob("*.md")):
        content = file_path.read_text(encoding="utf-8")
        meta = parse_yaml_frontmatter(content)
        # Claude expects frontmatter with name, description, model, and tools
        valid = bool(meta.get("name") and meta.get("model") and "tools" in meta)
        loaded_agents.append({
            "name": meta.get("name", file_path.stem),
            "model": meta.get("model"),
            "tools": meta.get("tools", []),
            "valid_frontmatter": valid,
            "path": str(file_path.relative_to(repo_root))
        })

    # Claude skills directory check (.claude/skills or .agent/skills)
    claude_skills_dir = repo_root / ".claude/skills"
    skills = []
    if claude_skills_dir.exists():
        for skill_dir in sorted(claude_skills_dir.iterdir()):
            if skill_dir.name.startswith("."):
                continue
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                meta = parse_yaml_frontmatter(skill_md.read_text(encoding="utf-8"))
                skills.append(meta.get("name", skill_dir.name))

    return {
        "status": "PASS" if loaded_agents and all(a.get("valid_frontmatter", a.get("valid_json")) for a in loaded_agents) else "FAIL",
        "agent_count": len(loaded_agents),
        "agents": loaded_agents,
        "skill_count": len(skills),
        "skills_sample": skills[:5]
    }

def verify_antigravity_projection(repo_root: Path):
    agents_dir = repo_root / ".agents"
    if not agents_dir.exists():
        return {"status": "FAIL", "error": f"Missing directory: {agents_dir}", "agents": []}
    
    loaded_agents = []
    for json_path in sorted(agents_dir.glob("*.json")):
        if json_path.name in ("manifest.json", "mcp_config.json", "settings.json", "skills.json", "plugins.json", "hooks.json"):
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            valid = bool(data.get("name") and data.get("model") and "tools" in data)
            loaded_agents.append({
                "name": data.get("name"),
                "model": data.get("model"),
                "tools": data.get("tools", []),
                "valid_json": valid,
                "path": str(json_path.relative_to(repo_root))
            })
        except Exception as e:
            loaded_agents.append({
                "file": json_path.name,
                "error": str(e),
                "valid_json": False
            })

    # Antigravity skills check (.agents/skills)
    skills_dir = repo_root / ".agents/skills"
    skills = []
    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.iterdir()):
            if skill_dir.name.startswith("."):
                continue
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                meta = parse_yaml_frontmatter(skill_md.read_text(encoding="utf-8"))
                skills.append(meta.get("name", skill_dir.name))

    return {
        "status": "PASS" if loaded_agents and all(a.get("valid_frontmatter", a.get("valid_json")) for a in loaded_agents) else "FAIL",
        "agent_count": len(loaded_agents),
        "agents": loaded_agents,
        "skill_count": len(skills),
        "skills_sample": skills[:5]
    }

def main():
    root = Path(".").resolve()
    print("==================================================")
    print("RUNTIME DISCOVERY VERIFICATION: CLAUDE & ANTIGRAVITY")
    print("==================================================")

    # 1. Claude Verification
    claude_res = verify_claude_projection(root)
    print(f"\n[CLAUDE CODE HARNESS]")
    print(f"Status: {claude_res['status']}")
    print(f"Loaded Agents Count: {claude_res.get('agent_count', 0)}")
    print(f"Available Skills Count: {claude_res.get('skill_count', 0)}")
    invalid_claude = [a['name'] for a in claude_res.get('agents', []) if not a.get('valid_frontmatter')]
    if invalid_claude:
        print(f"Invalid Agents: {invalid_claude}")
    else:
        print("All projected Claude agent markdown definitions have valid frontmatter.")

    # 2. Antigravity Verification
    agy_res = verify_antigravity_projection(root)
    print(f"\n[ANTIGRAVITY (AGY) HARNESS]")
    print(f"Status: {agy_res['status']}")
    print(f"Loaded Agents Count: {agy_res.get('agent_count', 0)}")
    print(f"Available Skills Count: {agy_res.get('skill_count', 0)}")
    invalid_agy = [a.get('name') or a.get('file') for a in agy_res.get('agents', []) if not a.get('valid_json')]
    if invalid_agy:
        print(f"Invalid Agents: {invalid_agy}")
    else:
        print("All projected Antigravity agent JSON definitions have valid schemas.")

    # 3. Canonical and Metadata Verification
    meta_path = root / ".agent/metadata.json"
    if meta_path.exists():
        with open(meta_path) as f:
            catalog = json.load(f)
        print(f"\n[CANONICAL METADATA]")
        print(f"Standard Agents Indexed: {len(catalog.get('agents', []))}")
        print(f"Canonical Adapters Indexed: {len(catalog.get('canonical_agents', []))}")
        print(f"Standard Skills Indexed: {len(catalog.get('skills', []))}")

    if claude_res['status'] == "PASS" and agy_res['status'] == "PASS":
        print("\nSUCCESS: Both Claude and Antigravity environments successfully loaded.")
        sys.exit(0)
    else:
        print("\nFAILURE: One or more harnesses failed verification.")
        sys.exit(1)

if __name__ == "__main__":
    main()
