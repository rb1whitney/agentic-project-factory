#!/usr/bin/env python3
"""
Stage 1: Deterministic Skill Library Parser (SaP §3.2).
Splits YAML frontmatter from SKILL.md body, segments by Markdown headings into
procedural units, and extracts code blocks, CLI commands, scripts, and references.
"""

import argparse
import json
import re
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$", re.MULTILINE)
FENCE_RE = re.compile(r"```([a-zA-Z0-9_-]*)\n(.*?)```", re.DOTALL)
INLINE_CMD_RE = re.compile(
    r"`((?:kubectl|gcloud|aws|terraform|gh|git|python3|/usr/bin/python3|bash|sh|ast-grep|helm|docker|uv|cargo|brew)\b[^`\n]+)`"
)
SCRIPT_REF_RE = re.compile(r"([\w./{}-]+\.(?:py|sh))")
MD_REF_RE = re.compile(r"([\w./{}-]+\.md)")


def parse_frontmatter(content: str) -> tuple[dict, str]:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    raw_fm = match.group(1)
    body = content[match.end() :]
    meta = {}
    for line in raw_fm.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        k, v = s.split(":", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if v:
            meta[k] = v
    return meta, body


def split_procedural_units(parent_name: str, body: str) -> list[dict]:
    matches = list(HEADING_RE.finditer(body))
    units = []
    if not matches:
        units.append(_build_unit(parent_name, 0, "Root", body))
        return units

    for idx, m in enumerate(matches):
        heading = m.group(2).strip()
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        section_text = body[start:end].strip()
        units.append(_build_unit(parent_name, idx, heading, section_text))
    return units


def _build_unit(parent_name: str, idx: int, heading: str, text: str) -> dict:
    code_blocks = []
    code_langs = []
    for fm in FENCE_RE.finditer(text):
        lang = (fm.group(1) or "text").strip().lower()
        code = fm.group(2).strip()
        if code:
            code_langs.append(lang)
            code_blocks.append(code)

    inline_cmds = [m.group(1).strip() for m in INLINE_CMD_RE.finditer(text)]
    all_code = "\n".join(code_blocks + inline_cmds)
    scripts = sorted(set(SCRIPT_REF_RE.findall(text + "\n" + all_code)))
    refs = sorted(set(MD_REF_RE.findall(text)))

    return {
        "unit_id": f"{parent_name}#u{idx}",
        "parent": parent_name,
        "heading": heading,
        "text": text,
        "code_langs": sorted(set(code_langs)),
        "code_blocks": code_blocks + inline_cmds,
        "linked_scripts": scripts,
        "references": refs,
    }


def parse_skill_library(skills_dir: Path) -> list[dict]:
    parents = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        content = skill_md.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)
        parent_name = meta.get("name", skill_dir.name)
        units = split_procedural_units(parent_name, body)

        scripts_dir = skill_dir / "scripts"
        bundled_scripts = (
            sorted(str(p.relative_to(skill_dir)) for p in scripts_dir.rglob("*") if p.is_file())
            if scripts_dir.is_dir()
            else []
        )
        refs_dir = skill_dir / "references"
        bundled_refs = (
            sorted(str(p.relative_to(skill_dir)) for p in refs_dir.glob("*.md"))
            if refs_dir.is_dir()
            else []
        )

        parents.append(
            {
                "name": parent_name,
                "description": meta.get("description", ""),
                "path": str(skill_md),
                "procedural_units": units,
                "scripts": bundled_scripts,
                "references": bundled_refs,
            }
        )
    return parents


def main():
    ap = argparse.ArgumentParser(description="SaP Stage 1: Parse SKILL.md library into parents.json")
    ap.add_argument("--skills-dir", default=".agent/skills", help="Path to skills directory")
    ap.add_argument("--out", default=".cache/sap/parents.json", help="Output JSON path")
    args = ap.parse_args()

    parents = parse_skill_library(Path(args.skills_dir))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(parents, indent=2) + "\n", encoding="utf-8")
    total_units = sum(len(p["procedural_units"]) for p in parents)
    print(f"Parsed {len(parents)} skills -> {total_units} procedural units at {out_path}")


if __name__ == "__main__":
    main()
