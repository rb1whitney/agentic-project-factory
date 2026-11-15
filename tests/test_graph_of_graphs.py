import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-code-map" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import eval_score  # noqa: E402
import graph_of_graphs as gog  # noqa: E402


def write_graph(path: Path, labels_by_community: dict) -> Path:
    nodes, links, prev = [], [], None
    for community, labels in labels_by_community.items():
        for label in labels:
            node_id = f"{label}_{community}"
            nodes.append(
                {
                    "id": node_id,
                    "label": label,
                    "community": community,
                    "file_type": "code",
                    "source_file": f"src/{label}.java",
                    "source_location": "L10",
                }
            )
            if prev:
                links.append({"source": node_id, "target": prev, "relation": "calls"})
            prev = node_id
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"nodes": nodes, "links": links}))
    return path


def make_index(tmp_path):
    a = write_graph(tmp_path / "a.json", {0: ["Alpha", "Beta", "Gamma"], 1: ["Delta"]})
    b = write_graph(tmp_path / "b.json", {0: ["Epsilon", "Zeta"]})
    return gog.build([("repo_a", str(a)), ("repo_b", str(b))], clones=None)


def test_build_summarizes_communities_largest_first(tmp_path):
    index = make_index(tmp_path)
    a = gog.find_repo(index, "repo_a")
    assert (a["nodes"], a["communities"]) == (4, 2)
    assert [c["size"] for c in a["top_communities"]] == [3, 1]
    assert index["dependencies_known"] is False


def test_overview_is_budgeted_and_points_deeper(tmp_path):
    text = gog.overview(make_index(tmp_path), limit=1)
    assert "2 repositories, 6 symbols" in text
    assert "dependencies not computed" in text
    assert "1 more repositories" in text
    assert text.splitlines()[-1].startswith("Go deeper: drill")


def test_drill_levels_cap_output_and_give_next_command(tmp_path):
    index = make_index(tmp_path)
    level1 = gog.drill(index, "repo_a", None, limit=1)
    assert "c0: 3 symbols" in level1 and "1 more communities" in level1
    level2 = gog.drill(index, "repo_a", "0", limit=2)
    assert "3 symbols" in level2 and "1 more symbols" in level2
    assert "src/" in level2 and ":10" in level2


def test_shared_names_do_not_create_cross_repo_edges(tmp_path):
    a = write_graph(tmp_path / "a.json", {0: ["os", "Alpha"]})
    b = write_graph(tmp_path / "b.json", {0: ["os", "Beta"]})
    index = gog.build([("a", str(a)), ("b", str(b))], clones=None)
    assert index["dependencies"] == []


def test_cli_build_and_overview(tmp_path):
    a = write_graph(tmp_path / "a.json", {0: ["Alpha"]})
    out = tmp_path / "gog.json"
    built = subprocess.run(
        [sys.executable, str(SCRIPTS / "graph_of_graphs.py"), "build", "--graph", f"a={a}", "--out", str(out)],
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stderr
    shown = subprocess.run(
        [sys.executable, str(SCRIPTS / "graph_of_graphs.py"), "overview", str(out)], capture_output=True, text=True
    )
    assert "1 repositories" in shown.stdout


def test_score_normalises_format_slips():
    reference = {"gson/src/A.java", "gson/src/B.java"}
    answer = "FILE: ./gson/src/A.java\nFILE: gson/gson/src/B.java\nFILE: gson/src/Extra.java\n"
    scored = eval_score.score_text(answer, reference, repo="gson")
    assert scored["matched"] == ["gson/src/A.java", "gson/src/B.java"]
    assert scored["extra"] == ["gson/src/Extra.java"]
    assert (scored["precision"], scored["recall"]) == (0.6667, 1.0)


def test_score_strips_absolute_root_and_handles_empty_answer():
    scored = eval_score.score_text("FILE: /work/repo/src/A.java", {"src/A.java"}, root="/work/repo")
    assert scored["f1"] == 1.0
    assert eval_score.prf(set(), {"a"}) == (0.0, 0.0, 0.0)
