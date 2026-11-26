"""Classes that share a simple name must stay separate, and references must resolve the way javac would."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-code-map" / "scripts"))

from graph_builder import GraphBuilder  # noqa: E402


def build(tmp_path, files):
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return GraphBuilder(str(tmp_path)).build_graph()


def targets(graph, source_file):
    """Files that `source_file` has an edge into."""
    nodes = graph["nodes"]
    return {nodes[e["to"]]["file"] for e in graph["edges"] if e["file"] == source_file} - {source_file}


def test_unique_class_keeps_its_simple_name(tmp_path):
    g = build(tmp_path, {"src/a/Key.java": "package a; public class Key {}"})
    assert "Key" in g["nodes"]


def test_same_name_in_two_packages_stays_two_nodes(tmp_path):
    g = build(
        tmp_path,
        {
            "src/a/Key.java": "package a; public class Key {}",
            "src/b/Key.java": "package b; public class Key {}",
        },
    )
    assert {"a.Key", "b.Key"} <= set(g["nodes"])
    assert "Key" not in g["nodes"]


def test_import_and_same_package_pick_the_right_class(tmp_path):
    g = build(
        tmp_path,
        {
            "src/a/Key.java": "package a; public class Key {}",
            "src/b/Key.java": "package b; public class Key {}",
            "src/a/UsesOwn.java": "package a; class UsesOwn { Key k; }",
            "src/c/UsesImport.java": "package c; import b.Key; class UsesImport { Key k; }",
            "src/c/UsesWildcard.java": "package c; import a.*; class UsesWildcard { Key k; }",
        },
    )
    assert targets(g, "src/a/UsesOwn.java") == {"src/a/Key.java"}
    assert targets(g, "src/c/UsesImport.java") == {"src/b/Key.java"}
    assert targets(g, "src/c/UsesWildcard.java") == {"src/a/Key.java"}


def test_import_of_a_library_class_does_not_link_to_a_project_class(tmp_path):
    g = build(
        tmp_path,
        {
            "src/a/List.java": "package a; public class List {}",
            "src/c/Uses.java": "package c; import java.util.List; class Uses { List xs; }",
        },
    )
    assert targets(g, "src/c/Uses.java") == set()


def test_twin_source_trees_with_the_same_package_stay_separate(tmp_path):
    files = {}
    for root in ("jre/src", "android/src"):
        files[f"{root}/p/Box.java"] = "package p; public class Box { static void open() {} }"
        files[f"{root}/p/User.java"] = "package p; class User { void go() { Box.open(); } }"
    g = build(tmp_path, files)
    assert targets(g, "jre/src/p/User.java") == {"jre/src/p/Box.java"}
    assert targets(g, "android/src/p/User.java") == {"android/src/p/Box.java"}


def test_reference_that_cannot_be_decided_is_counted_not_guessed(tmp_path):
    g = build(
        tmp_path,
        {
            "one/p/Box.java": "package p; public class Box {}",
            "two/p/Box.java": "package p; public class Box {}",
            "other/q/Uses.java": "package q; import p.Box; class Uses { Box b; }",
        },
    )
    assert targets(g, "other/q/Uses.java") == set()
    assert g["stats"]["java_ambiguous_references"] >= 1


def test_calls_and_inheritance_follow_the_resolved_class(tmp_path):
    g = build(
        tmp_path,
        {
            "src/a/Base.java": "package a; public class Base { public void run() {} }",
            "src/b/Base.java": "package b; public class Base { public void run() {} }",
            "src/c/Child.java": "package c; import b.Base; class Child extends Base { void go() { run(); } }",
        },
    )
    assert targets(g, "src/c/Child.java") == {"src/b/Base.java"}
    assert any(e["type"] == "calls" and e["to"] == "b.Base.run" for e in g["edges"])


def test_nested_class_is_resolved_from_its_outer_class(tmp_path):
    g = build(
        tmp_path,
        {
            "src/a/Outer.java": "package a; class Outer { static class Item {} Item i; }",
            "src/b/Item.java": "package b; public class Item {}",
        },
    )
    assert targets(g, "src/a/Outer.java") == set()
    assert any(e["from"] == "Outer" and e["to"] == "Outer.Item" for e in g["edges"])


def test_closure_says_when_a_name_means_several_classes(tmp_path):
    from semantic_query import SemanticQuery

    g = build(
        tmp_path,
        {
            "src/a/Key.java": "package a; public class Key {}",
            "src/b/Key.java": "package b; public class Key {}",
        },
    )
    out = SemanticQuery.from_dict(g).closure("Key")
    assert "2 classes are named 'Key'" in out
    assert "a.Key" in out and "b.Key" in out


def test_low_memory_build_gives_the_same_graph(tmp_path, monkeypatch):
    files = {
        "src/a/Base.java": "package a; public class Base { public void run() {} static class In {} }",
        "src/c/Child.java": "package c; import a.Base; class Child extends Base { void go() { run(); } }",
    }
    kept = build(tmp_path, files)
    monkeypatch.setattr(GraphBuilder, "KEEP_TREES_MAX_FILES", 0)
    reparsed = build(tmp_path, files)
    assert reparsed["nodes"] == kept["nodes"]
    assert reparsed["edges"] == kept["edges"]
