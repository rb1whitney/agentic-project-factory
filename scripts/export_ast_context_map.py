#!/usr/bin/env python3
"""Export skill-code-map + skill-graphify as the standalone `ast-context-map` repository tree.

The hub is the source of truth; the output is generated (never hand-edited).
Usage: python3 scripts/export_ast_context_map.py <empty-output-dir>
"""
import re
import shutil
import sys
from pathlib import Path

HUB = Path(__file__).resolve().parents[1]
CM = HUB / ".agent/skills/skill-code-map"
GR = HUB / ".agent/skills/skill-graphify"
TEMPLATES = Path(__file__).resolve().parent / "export_templates" / "ast-context-map"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")

TESTS = [
    "test_ast_grep_rules", "test_code_mapper", "test_env_diff", "test_external_cache", "test_go_graph",
    "test_graph_registry", "test_k8s_catalog", "test_k8s_catalog_merge", "test_k8s_graphify",
    "test_k8s_graphify_edges", "test_live_uri_ranking", "test_semantic_lineage", "test_state_graph",
    "test_terraform_bridge",
]

# Doc rewrites: hub layout -> standalone layout. The hub-only `| bin/rtk` output filter is dropped.
DOC_RULES = [
    (r" and pipe shell output through `bin/rtk`", ""),
    (r"[ \t]*\|[ \t]*bin/rtk\b", ""),
    (r"/usr/bin/python3", "python3"),
    (r"\.agent/skills/skill-code-map/(scripts|resources|references)/", r"\1/"),
    (r"\.agent/skills/skill-code-map/", ""),
    (r"\.agent/skills/skill-graphify/references/", "references/"),
    (r"\.agent/skills/skill-graphify/", "skills/graphify/"),
]
TEST_RULES = [
    (r'parents\[1\] / "\.agent" / "skills"', "parents[1]"),
    (r'"skill-code-map" / "scripts"', '"scripts"'),
    (r"\.agent/skills/skill-code-map/scripts/", "scripts/"),
]


def rewrite(text: str, rules) -> str:
    for pat, repl in rules:
        text = re.sub(pat, repl, text)
    return text


def main(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        sys.exit(f"refusing to write into non-empty directory: {out}")
    shutil.copytree(TEMPLATES, out, dirs_exist_ok=True, ignore=IGNORE)
    for sub in ("scripts", "resources", "references"):
        shutil.copytree(CM / sub, out / sub, dirs_exist_ok=True, ignore=IGNORE)
    shutil.copytree(GR / "references", out / "references", dirs_exist_ok=True, ignore=IGNORE)
    (out / "SKILL.md").write_text(rewrite((CM / "SKILL.md").read_text(), DOC_RULES))
    (out / "skills/graphify").mkdir(parents=True)
    (out / "skills/graphify/SKILL.md").write_text(rewrite((GR / "SKILL.md").read_text(), DOC_RULES))
    for md in list((out / "references").glob("*.md")) + list((out / "resources").rglob("*.md")):
        md.write_text(rewrite(md.read_text(), DOC_RULES))
    (out / "tests").mkdir(exist_ok=True)
    for name in TESTS:
        src = (HUB / "tests" / f"{name}.py").read_text()
        (out / "tests" / f"{name}.py").write_text(rewrite(src, TEST_RULES))
    shutil.copy(HUB / "LICENSE", out / "LICENSE")
    print(f"exported to {out}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]).resolve())
