#!/usr/bin/env python3
"""
Multi-Harness Hydration Engine (v2.1)
Translates canonical agent definitions (.agent/agents/*.yaml) into:
- Claude Code:   .claude/agents/*.md
- Antigravity:   .agents/agents/*.md & .agents/*.json
- Codex:         .codex/agents/*.toml
"""

import json
import re
import sys
from pathlib import Path

import yaml

CANONICAL_DIR = Path(".agent/agents")
SKILLS_DIR = Path(".agent/skills")
MAP_FILE = Path(".agent/adapters/map.yaml")

def load_map():
    if not MAP_FILE.exists():
        print(f"Configuration Error: Adapter map '{MAP_FILE}' not found.", file=sys.stderr)
        sys.exit(1)
    with open(MAP_FILE, "r") as f:
        data = yaml.safe_load(f)
    return data

def parse_agent_file(path, map_data):
    with open(path, "r") as f:
        content = f.read()

    header_str = ""
    body = ""
    if content.startswith("---"):
        match = re.match(r"^---\s*\n(.*?)\n---\s*(\n|$)(.*)$", content, re.DOTALL)
        if match:
            header_str = match.group(1)
            body = match.group(3).strip()
    else:
        match = re.match(r"^(.*?)\n---\s*(\n|$)(.*)$", content, re.DOTALL)
        if match:
            header_str = match.group(1)
            body = match.group(3).strip()

    if not header_str:
        header_str = content
        body = ""

    try:
        header = yaml.safe_load(header_str) or {}
    except Exception as e:
        print(f"Validation Error: '{path}' has malformed YAML header: {e}", file=sys.stderr)
        sys.exit(1)

    name = header.get("name")
    if not name:
        print(f"Validation Error: '{path}' missing required 'name' field.", file=sys.stderr)
        sys.exit(1)

    description = header.get("description", "")
    if not description:
        print(f"Validation Error: '{path}' missing required 'description' field.", file=sys.stderr)
        sys.exit(1)

    tier = header.get("tier")
    capabilities = header.get("capabilities")
    skills = header.get("skills", [])
    returns = header.get("returns")
    role = header.get("role", "worker")

    # Strict Fail Loud Invariant: No fallback guessing allowed
    if not capabilities or not tier:
        print(
            f"Validation Error: '{path}' missing required 'capabilities' or 'tier'. "
            "Fail-loud invariant triggered.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Pre-Flight Validation Rules
    allowed_caps = {"read", "search", "write", "shell", "web", "delegate"}
    for c in capabilities:
        if c not in allowed_caps:
            print(f"Validation Error: Unknown capability '{c}' in '{path}'. Must be in {allowed_caps}", file=sys.stderr)
            sys.exit(1)

    # Worker vs Orchestrator constraint
    if "delegate" in capabilities and role != "orchestrator":
        if "supervisor" in name or "orchestrator" in name:
            role = "orchestrator"
        else:
            print(f"Security Error: Non-orchestrator agent '{name}' holds 'delegate' capability.", file=sys.stderr)
            sys.exit(1)

    return {
        "path": str(path),
        "name": name,
        "description": description,
        "role": role,
        "tier": tier,
        "capabilities": capabilities,
        "skills": skills,
        "returns": returns,
        "body": body,
    }

def hydrate_claude(agents, map_data, provider="native"):
    harnesses = map_data.get("harnesses", map_data)
    claude_cfg = harnesses.get("claude", {})
    out_dir = Path(".claude/agents")
    out_dir.mkdir(parents=True, exist_ok=True)
    cap_map = claude_cfg.get("capabilities", {})
    tier_map = claude_cfg.get("tiers", {})
    disallowed_default = claude_cfg.get("disallowed_when_no_delegate", ["Task", "Agent"])

    # Prune stale output files
    expected_files = {f"{agent['name']}.md" for agent in agents}
    for existing in out_dir.glob("*.md"):
        if existing.name not in expected_files:
            print(f"Pruning stale Claude artifact: {existing}")
            existing.unlink()

    for agent in agents:
        tier = agent["tier"]
        model = tier_map.get(tier, "sonnet")

        tools = []
        for cap in agent["capabilities"]:
            if cap in cap_map:
                tools.extend(cap_map[cap])

        frontmatter = {
            "name": agent["name"],
            "description": agent["description"],
            "model": model,
            "tools": tools,
        }

        if "delegate" not in agent["capabilities"]:
            frontmatter["disallowedTools"] = disallowed_default

        if agent["skills"]:
            frontmatter["skills"] = agent["skills"]

        if "read" in agent["capabilities"] and "write" not in agent["capabilities"]:
            frontmatter["permissionMode"] = "plan"

        body = agent["body"]
        if agent["returns"] and "write" not in agent["capabilities"]:
            body = (
                "## Return Contract (Read-Only Subagent)\n"
                f"Do NOT attempt to write '{agent['returns']}' directly to disk. Return the complete, formatted "
                "report as text in your final response so the orchestrator can write it.\n\n"
            ) + body

        out_path = out_dir / f"{agent['name']}.md"
        with open(out_path, "w") as f:
            f.write("---\n")
            f.write(f"# GENERATED from {agent['path']} by harness adapter. Do not edit.\n")
            yaml.dump(frontmatter, f, default_flow_style=False, sort_keys=False)
            f.write("---\n\n")
            f.write(body)
            f.write("\n")
        print(f"Hydrated Claude agent: {out_path}")


def hydrate_antigravity(agents, map_data, provider="native"):
    harnesses = map_data.get("harnesses", map_data)
    agy_cfg = harnesses.get("antigravity", {})
    out_dir_md = Path(".agents/agents")
    out_dir_json = Path(".agents")
    out_dir_md.mkdir(parents=True, exist_ok=True)
    out_dir_json.mkdir(parents=True, exist_ok=True)

    cap_map = agy_cfg.get("capabilities", {})
    tier_map = agy_cfg.get("tiers", {})
    auto_approve_caps = agy_cfg.get("auto_approve_capabilities", ["read", "search"])

    # Prune stale output files
    expected_json = {f"{agent['name']}.json" for agent in agents}
    ignored_json = {
        "manifest.json",
        "mcp_config.json",
        "settings.json",
        "skills.json",
        "plugins.json",
        "hooks.json",
    }
    for existing in out_dir_json.glob("*.json"):
        if existing.name in ignored_json:
            continue
        if existing.name not in expected_json:
            print(f"Pruning stale Antigravity JSON artifact: {existing}")
            existing.unlink()

    expected_md = {f"{agent['name']}.md" for agent in agents}
    for existing in out_dir_md.glob("*.md"):
        if existing.name not in expected_md:
            print(f"Pruning stale Antigravity MD artifact: {existing}")
            existing.unlink()

    for agent in agents:
        tier = agent["tier"]
        model = tier_map.get(tier, "flash")

        tools = []
        auto_approve = []
        for cap in agent["capabilities"]:
            if cap in cap_map:
                mapped_tools = cap_map[cap]
                tools.extend(mapped_tools)
                if cap in auto_approve_caps:
                    auto_approve.extend(mapped_tools)

        json_spec = {
            "name": agent["name"],
            "description": agent["description"],
            "model": model,
            "subagent": True,
            "commandExecutionPolicy": "sandbox",
            "tools": tools,
            "auto_approve": auto_approve
        }

        json_out_path = out_dir_json / f"{agent['name']}.json"
        with open(json_out_path, "w") as f:
            json.dump(json_spec, f, indent=2)
            f.write("\n")

        # Markdown representation with parity on commandExecutionPolicy and auto_approve
        frontmatter = {
            "name": agent["name"],
            "description": agent["description"],
            "model": model,
            "subagent": True,
            "commandExecutionPolicy": "sandbox",
            "tools": tools,
            "auto_approve": auto_approve,
            "skills": [f"skills/{s}" if not s.startswith("skills/") else s for s in agent["skills"]]
        }
        body = agent["body"]
        if agent["returns"] and "write" not in agent["capabilities"]:
            body = (
                "## Return Contract (Read-Only Subagent)\n"
                f"Do NOT attempt to write '{agent['returns']}' directly to disk. Return the complete, formatted "
                "report as text in your final response so the orchestrator can write it.\n\n"
            ) + body

        md_out_path = out_dir_md / f"{agent['name']}.md"
        with open(md_out_path, "w") as f:
            f.write("---\n")
            f.write(f"# GENERATED from {agent['path']} by harness adapter. Do not edit.\n")
            yaml.dump(frontmatter, f, default_flow_style=False, sort_keys=False)
            f.write("---\n\n")
            f.write(body)
            f.write("\n")

        print(f"Hydrated Antigravity agent: {json_out_path}")

def hydrate_codex(agents, map_data, provider="native"):
    harnesses = map_data.get("harnesses", map_data)
    providers = map_data.get("providers", {})
    codex_cfg = harnesses.get("codex", {})
    out_dir = Path(".codex/agents")
    out_dir.mkdir(parents=True, exist_ok=True)
    tier_map = codex_cfg.get("tiers", {})

    provider_cfg = providers.get(provider, {})
    provider_tiers = provider_cfg.get("tiers", {})

    # Prune stale output files
    expected_toml = {f"{agent['name']}.toml" for agent in agents}
    for existing in out_dir.glob("*.toml"):
        if existing.name not in expected_toml:
            print(f"Pruning stale Codex artifact: {existing}")
            existing.unlink()

    for agent in agents:
        tier = agent["tier"]
        if provider != "native" and tier in provider_tiers:
            model = provider_tiers[tier]
        else:
            model = tier_map.get(tier, "gpt-5-turbo")

        if "write" in agent["capabilities"] or "shell" in agent["capabilities"]:
            sandbox_mode = "workspace-write"
        else:
            sandbox_mode = "read-only"

        name_snake = agent["name"].replace("-", "_")

        instructions = []
        if agent["skills"]:
            skills_str = ", ".join(agent["skills"])
            instructions.append(f"Start by reading the following skills: {skills_str}.\n")

        if "web" not in agent["capabilities"]:
            instructions.append("ADVISORY (not enforced by Codex): do not use web search.\n")

        if "delegate" not in agent["capabilities"]:
            instructions.append("ADVISORY (not enforced by Codex): do not delegate or spawn subagents.\n")

        if agent["returns"] and "write" not in agent["capabilities"]:
            instructions.append(
                f"ADVISORY: You are in read-only sandbox mode. Hand back the '{agent['returns']}' content "
                "in your response rather than attempting to write the file directly.\n"
            )

        instructions.append(agent["body"])
        dev_instructions_str = "\n".join(instructions)
        escaped_instructions = dev_instructions_str.replace('"""', '\\"\\"\\"')

        out_path = out_dir / f"{agent['name']}.toml"
        with open(out_path, "w") as f:
            f.write(f'# GENERATED from {agent["path"]} by harness adapter. Do not edit.\n')
            f.write(f'name = "{name_snake}"\n')
            f.write(f'description = "{agent["description"]}"\n')
            f.write(f'model = "{model}"\n')
            if provider != "native":
                f.write(f'model_provider = "{provider}"\n')
            f.write(f'sandbox_mode = "{sandbox_mode}"\n')
            f.write('developer_instructions = """\n')
            f.write(escaped_instructions)
            f.write('\n"""\n')
        print(f"Hydrated Codex agent: {out_path}")


def main():
    target = "all"
    provider = "native"

    for arg in sys.argv[1:]:
        if arg.startswith("--provider="):
            provider = arg.split("=", 1)[1]
        elif not arg.startswith("--"):
            target = arg

    valid_targets = ["claude", "antigravity", "codex", "all"]
    if target not in valid_targets:
        print(
            "Usage: python3 scripts/hydrate.py [claude | antigravity | codex | all] [--provider=native|openrouter]",
            file=sys.stderr,
        )
        sys.exit(1)

    map_data = load_map()
    yaml_files = sorted(CANONICAL_DIR.glob("*.yaml"))
    if not yaml_files:
        print(f"Error: No agent definition files found in '{CANONICAL_DIR}'", file=sys.stderr)
        sys.exit(1)

    agents = [parse_agent_file(f, map_data) for f in yaml_files]

    if target in ["claude", "all"]:
        hydrate_claude(agents, map_data, provider=provider)
    if target in ["antigravity", "all"]:
        hydrate_antigravity(agents, map_data, provider=provider)
    if target in ["codex", "all"]:
        hydrate_codex(agents, map_data, provider=provider)

if __name__ == "__main__":
    main()
