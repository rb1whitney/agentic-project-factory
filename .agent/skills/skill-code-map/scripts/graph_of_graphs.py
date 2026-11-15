#!/usr/bin/env python3
"""Graph of graphs: a budgeted, drillable index over many per-repository code graphs (Graphify node_link JSON).

Levels: repositories (0) -> communities (1) -> symbols (2). Every view takes --limit and ends with the exact command
that goes one level deeper, so an agent reads a small answer first and expands only where it needs to.

Cross-repository edges come only from dependencies declared in package manifests (see manifest_deps.py). Shared
standard-library names are deliberately NOT used as links: merging graphs by node id connects repositories because they
all import `os` or `java.util`, not because one depends on another.

  graph_of_graphs.py build --graphs-dir DIR --repos gson guava [--clones DIR] --out gog.json
  graph_of_graphs.py build --graph gson=path/to/graph.json --graph guava=other.json --out gog.json
  graph_of_graphs.py overview gog.json [--limit 10]
  graph_of_graphs.py drill gog.json REPO [COMMUNITY] [--limit 10]

`--graphs-dir` expects DIR/<repo>/graphify-out/graph.json. `--clones` is a directory of git clones and enables
dependency edges; without it the index has none and says so.
"""

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest_deps  # noqa: E402

STORED_COMMUNITIES = 60


def load_graph(path: str) -> dict:
    return json.loads(Path(path).read_text())


def line_of(location) -> str:
    m = re.search(r"(\d+)", str(location or ""))
    return m.group(1) if m else "?"


def summarize(name: str, graph_path: str, keep: int = STORED_COMMUNITIES) -> dict:
    graph = load_graph(graph_path)
    nodes, links = graph["nodes"], graph["links"]
    community_of = {n["id"]: n.get("community") for n in nodes}
    degree = collections.Counter()
    for link in links:
        degree[link["source"]] += 1
        degree[link["target"]] += 1
    members = collections.defaultdict(list)
    for n in nodes:
        members[n.get("community")].append(n)
    neighbours = collections.defaultdict(collections.Counter)
    for link in links:
        a, b = community_of.get(link["source"]), community_of.get(link["target"])
        if a is not None and b is not None and a != b:
            neighbours[a][b] += 1
    communities = []
    for cid, group in sorted(members.items(), key=lambda kv: -len(kv[1])):
        by_degree = sorted(group, key=lambda n: -degree[n["id"]])
        files = collections.Counter(n.get("source_file") for n in group if n.get("source_file"))
        communities.append(
            {
                "id": cid,
                "size": len(group),
                "labels": [n["label"] for n in by_degree[:4]],
                "files": [f for f, _ in files.most_common(3)],
                "neighbours": [[b, w] for b, w in neighbours[cid].most_common(3)],
            }
        )
    return {
        "name": name,
        "graph": str(Path(graph_path).resolve()),
        "nodes": len(nodes),
        "links": len(links),
        "communities": len(members),
        "top_communities": communities[:keep],
    }


def build(specs: list[tuple[str, str]], clones: str | None) -> dict:
    repos = [summarize(name, path) for name, path in specs]
    out = {"version": 1, "repos": repos, "dependencies": [], "dependencies_known": bool(clones)}
    if clones:
        root = Path(clones)
        present = [r["name"] for r in repos if (root / r["name"] / ".git").exists()]
        derived = manifest_deps.derive(root, present)
        out["dependencies"] = [
            {"from": e["from"], "to": e["to"], "dependency": e["dependency"], "evidence": e["evidence"]}
            for e in derived["edges"]
        ]
    return out


def overview(gog: dict, limit: int) -> str:
    repos = sorted(gog["repos"], key=lambda r: -r["nodes"])
    deps = gog["dependencies"]
    lines = [
        f"{len(repos)} repositories, {sum(r['nodes'] for r in repos)} symbols, "
        + (
            f"{len(deps)} declared dependencies"
            if gog["dependencies_known"]
            else "dependencies not computed (pass --clones)"
        )
    ]
    out_deg = collections.Counter(d["from"] for d in deps)
    in_deg = collections.Counter(d["to"] for d in deps)
    for r in repos[:limit]:
        lines.append(
            f"- {r['name']}: {r['nodes']} symbols, {r['communities']} communities, "
            f"depends on {out_deg[r['name']]}, used by {in_deg[r['name']]}"
        )
    for d in deps[: limit * 2]:
        lines.append(f"  {d['from']} -> {d['to']} via {d['dependency']}")
    if len(repos) > limit:
        lines.append(f"... {len(repos) - limit} more repositories. All: overview --limit {len(repos)}")
    lines.append("Go deeper: drill <REPO>")
    return "\n".join(lines)


def find_repo(gog: dict, name: str) -> dict:
    for r in gog["repos"]:
        if r["name"] == name:
            return r
    sys.exit(f"unknown repository {name!r}; known: {', '.join(r['name'] for r in gog['repos'])}")


def drill(gog: dict, repo: str, community: str | None, limit: int) -> str:
    entry = find_repo(gog, repo)
    if community is None:
        shown = entry["top_communities"][:limit]
        lines = [f"{repo}: {entry['communities']} communities (largest first)"]
        for c in shown:
            lines.append(f"- c{c['id']}: {c['size']} symbols | {', '.join(c['labels'])} | {', '.join(c['files'][:2])}")
        rest = entry["communities"] - len(shown)
        if rest > 0:
            lines.append(
                f"... {rest} more communities. More: drill {repo} --limit {min(entry['communities'], limit * 2)}"
            )
        lines.append(f"Go deeper: drill {repo} <community id>")
        return "\n".join(lines)
    wanted = None if community.lower() in ("none", "null") else int(community.lstrip("c"))
    graph = load_graph(entry["graph"])
    degree = collections.Counter()
    for link in graph["links"]:
        degree[link["source"]] += 1
        degree[link["target"]] += 1
    group = sorted((n for n in graph["nodes"] if n.get("community") == wanted), key=lambda n: -degree[n["id"]])
    lines = [f"{repo} c{community}: {len(group)} symbols (most connected first)"]
    for n in group[:limit]:
        lines.append(
            f"- {n['label']}  {n.get('source_file')}:{line_of(n.get('source_location'))}  links={degree[n['id']]}"
        )
    if len(group) > limit:
        lines.append(f"... {len(group) - limit} more symbols. More: drill {repo} {community} --limit {len(group)}")
    lines.append("Go deeper: semantic_query.py impact <label> (needs a code_mapper graph) or read the file")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--graph", action="append", default=[], metavar="NAME=PATH")
    b.add_argument("--graphs-dir")
    b.add_argument("--repos", nargs="+", default=[])
    b.add_argument("--clones")
    b.add_argument("--out", required=True)
    o = sub.add_parser("overview")
    o.add_argument("gog")
    o.add_argument("--limit", type=int, default=10)
    d = sub.add_parser("drill")
    d.add_argument("gog")
    d.add_argument("repo")
    d.add_argument("community", nargs="?")
    d.add_argument("--limit", type=int, default=10)
    a = ap.parse_args()
    if a.cmd == "build":
        specs = [tuple(s.split("=", 1)) for s in a.graph]
        specs += [(r, str(Path(a.graphs_dir) / r / "graphify-out" / "graph.json")) for r in a.repos]
        if not specs:
            sys.exit("give --graph NAME=PATH or --graphs-dir with --repos")
        gog = build(specs, a.clones)
        Path(a.out).write_text(json.dumps(gog))
        print(f"wrote {a.out}: {len(gog['repos'])} repositories, {len(gog['dependencies'])} declared dependencies")
        return
    gog = json.loads(Path(a.gog).read_text())
    print(overview(gog, a.limit) if a.cmd == "overview" else drill(gog, a.repo, a.community, a.limit))


if __name__ == "__main__":
    main()
