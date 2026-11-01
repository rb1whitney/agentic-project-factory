#!/usr/bin/env python3
"""
Physical Skill & Agent Consolidation Engine (SaP §3.5, §5.6).
Consolidates 55 fragmented skills into 13 Core Parent Skills:
1. Migrates all child scripts/ and references/*.md into their Core Parent Skill.
2. Converts child SKILL.md bodies into {PARENT}/references/<child>.md runbooks.
3. Removes the 42 absorbed child skill directories from .agent/skills/ and prunes
   duplicate agent .agent/agents/sre-specialist.yaml.
"""

import shutil
from pathlib import Path

from scripts.sap.verifier import _strip_sap_bundle

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".agent/skills"
AGENTS_DIR = REPO_ROOT / ".agent/agents"

CONSOLIDATION_MAP = {
    "skill-code-map": [
        "skill-context-master",
        "skill-codebase-recon",
    ],
    "skill-graphify": [
        "skill-crossplane",
    ],
    "skill-kubernetes": [
        "skill-kubernetes-local",
    ],
    "skill-aws": [
        "skill-aws-foundation",
        "skill-aws-serverless",
        "skill-aws-sagemaker",
        "skill-aws-migration",
        "skill-finops",
    ],
    "skill-gcp": [
        "skill-gcp-setup",
        "skill-gcp-mcp-setup",
        "skill-gcp-playbooks",
    ],
    "skill-sre-investigation": [
        "skill-sre-advanced",
        "skill-sre-governance",
        "skill-observability",
        "skill-data-ingestion",
    ],
    "skill-terraform": [
        "skill-packer",
        "skill-network",
        "skill-certificate-manager",
        "skill-on-prem-provisioning",
    ],
    "skill-github": [
        "skill-pr-creator",
        "skill-ci-replicator",
        "skill-review-suite",
        "skill-docs",
    ],
    "skill-compliance-auditor": [
        "skill-behavioral-evals",
    ],
    "skill-conductor": [
        "skill-swarm",
        "skill-swarm-agents",
        "skill-swarm-management",
        "skill-ddd",
        "skill-architecture",
        "skill-product_blueprint",
    ],
    "skill-factory-compiler": [
        "skill-harness-models",
        "skill-nexus-sync",
        "skill-webhook-autoload",
        "skill-agentic-initializer",
    ],
    "skill-always-on-memory": [
        "skill-episodic-memory",
        "skill-graph-memory",
    ],
    "skill-platform-admin": [
        "skill-mcp-manager",
        "skill-opencode",
        "skill-gemini",
        "skill-msbuild",
        "skill-frontend",
    ],
}


def merge_child_into_parent(parent_name: str, child_name: str) -> dict:
    parent_dir = SKILLS_DIR / parent_name
    child_dir = SKILLS_DIR / child_name
    if not child_dir.exists():
        return {"scripts": 0, "refs": 0}

    parent_refs = parent_dir / "references"
    parent_refs.mkdir(parents=True, exist_ok=True)

    moved_scripts = 0
    moved_refs = 0

    # 1. Convert child SKILL.md into {parent}/references/{child_stem}.md
    child_md = child_dir / "SKILL.md"
    if child_md.exists():
        clean_body = _strip_sap_bundle(child_md.read_text(encoding="utf-8")).strip()
        short_name = child_name.replace("skill-", "").replace("_", "-")
        dest_ref = parent_refs / f"{short_name}.md"
        dest_ref.write_text(clean_body + "\n", encoding="utf-8")
        moved_refs += 1

    # 2. Copy all child references/* into {parent}/references/
    child_refs = child_dir / "references"
    if child_refs.is_dir():
        for rf in sorted(child_refs.rglob("*")):
            if rf.is_file():
                rel = rf.relative_to(child_refs)
                target = parent_refs / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copy2(rf, target)
                    moved_refs += 1

    # 3. Copy all child scripts/* into {parent}/scripts/
    child_scripts = child_dir / "scripts"
    if child_scripts.is_dir():
        parent_scripts = parent_dir / "scripts"
        parent_scripts.mkdir(parents=True, exist_ok=True)
        for sf in sorted(child_scripts.rglob("*")):
            if sf.is_file() and "__pycache__" not in str(sf):
                rel = sf.relative_to(child_scripts)
                target = parent_scripts / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copy2(sf, target)
                    moved_scripts += 1

    # 4. Remove absorbed child skill directory
    shutil.rmtree(child_dir)
    return {"scripts": moved_scripts, "refs": moved_refs}


def main():
    total_removed = 0
    total_scripts = 0
    total_refs = 0

    for parent, children in CONSOLIDATION_MAP.items():
        for child in children:
            if (SKILLS_DIR / child).exists():
                stats = merge_child_into_parent(parent, child)
                total_removed += 1
                total_scripts += stats["scripts"]
                total_refs += stats["refs"]

    # Prune duplicate sre-specialist.yaml (consolidated into specialist-sre.yaml)
    dup_agent = AGENTS_DIR / "sre-specialist.yaml"
    if dup_agent.exists():
        dup_agent.unlink()
        print("Removed duplicate agent: .agent/agents/sre-specialist.yaml (canonical: specialist-sre.yaml)")

    remaining_skills = sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and not d.name.startswith("."))
    remaining_agents = sorted(p.stem for p in AGENTS_DIR.glob("*.yaml"))
    print(
        f"Consolidated {total_removed} child skills into {len(remaining_skills)} Core Parent Skills "
        f"(migrated {total_scripts} scripts, {total_refs} references)."
    )
    print(f"Active Core Parent Skills ({len(remaining_skills)}): {remaining_skills}")
    print(f"Active Canonical Agents ({len(remaining_agents)}): {remaining_agents}")


if __name__ == "__main__":
    main()
