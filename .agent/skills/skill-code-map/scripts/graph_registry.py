#!/usr/bin/env python3
"""Shared registry for per-repo Graphify graphs: publish, route, fetch, query.

CI runs `graphify extract <repo> --code-only`, then `publish` stores one immutable gzip graph per commit plus a small
catalog entry. Readers call `route` to find which repo answers a question, then `query` to ask that repo's graph
without a checkout. The store is a local directory today; the Store interface is the seam for a bucket later.

Layout under the store root:
  graphs/<repo>/<sha>/graph.json.gz   immutable
  graphs/<repo>/latest.json           {sha, branch, built_at, graphify_version}
  catalog/<repo>.json                 one file per repo, so concurrent publishes never race on one file

Exit codes (mirror `graphify query`): 0 answer, 3 ambiguous (candidates listed), 4 no match, 2 usage or store error.
"""

import argparse
import gzip
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
STOP = set(
    (
        "the a of and or to in is for self cls init main test tests get set new from import str int "
        "com org java src lib util impl base api"
    ).split()
)
# Generated, vendored or minified paths add vocabulary that is not the repo's own design.
GENERATED = re.compile(
    r"(chunk-|main-[A-Z0-9]{6,}|\.min\.|_generated|\.lock$|package-lock|node_modules|/dist/|/third_party/)"
)
TESTLIKE = re.compile(
    r"(^|/)(tests?|testing|testdata|benchmarks?|examples?|fixtures?)(/|$)|Tests?\.[a-z]+$|_test\.[a-z]+$", re.I
)
STRUCTURAL = {"contains", "method", "calls", "implements", "inherits", "extends"}
# Uncalibrated defaults: chosen on one 20-question set authored by the assistant. Recalibrate on real questions.
DEFAULT_FLOOR = 4.0
DEFAULT_RATIO = 1.5
README_WEIGHT = 3
MAX_TOKENS = 4000
# Words that open a how-to question but name no repo. Applied to questions only, never to the index.
QUESTION_FILLER = set(
    (
        "how what when which where why does should would could can need want use used using correctly proper properly "
        "best practice practices across large optimal optimize effective strategies implement configure "
        "handle structure "
        "define write execute create build make setup between difference compared compare performance implications"
    ).split()
)
# A repo named in the question is the strongest routing signal there is; a hub symbol named in it is a weaker one.
NAME_BOOST = 8.0
HUB_BOOST = 3.0


class StoreError(Exception):
    pass


def _check_name(value, what):
    if not NAME_RE.match(value or ""):
        raise StoreError(f"invalid {what}: {value!r} (allowed: letters, digits, . _ -)")
    return value


class LocalStore:
    """Directory-backed store. Files are written 0600 and replaced atomically."""

    def __init__(self, root):
        self.root = Path(root).expanduser()

    def path(self, *parts):
        return self.root.joinpath(*parts)

    def put(self, rel, data):
        dest = self.path(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            os.chmod(tmp, 0o600)
            os.replace(tmp, dest)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def get(self, rel):
        p = self.path(rel)
        if not p.is_file():
            raise StoreError(f"not in store: {rel}")
        return p.read_bytes()

    def exists(self, rel):
        return self.path(rel).is_file()

    def list(self, prefix):
        d = self.path(prefix)
        return sorted(p.name for p in d.iterdir()) if d.is_dir() else []


def open_store(uri):
    if re.match(r"^(s3|gs)://", uri or ""):
        raise StoreError(f"{uri.split(':')[0]}:// store is not implemented yet; use a local directory")
    return LocalStore(uri)


def toks(text):
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text or "")
    return [t for t in re.split(r"[^A-Za-z0-9]+", text.lower()) if len(t) > 2 and t not in STOP and not t.isdigit()]


def hubs(nodes, links, limit=10):
    """Most-connected nodes that look like architecture: defined in repo code, with outgoing structure.

    Excludes tests, benchmarks, generated files, externals (no source file) and annotation-like nodes that are only
    ever imported or referenced.
    """
    deg, structural = Counter(), Counter()
    for e in links:
        deg[e["source"]] += 1
        deg[e["target"]] += 1
        if e.get("relation") in STRUCTURAL:
            structural[e["source"]] += 1
    by = {n["id"]: n for n in nodes}
    out, seen = [], set()
    for nid, _ in deg.most_common(len(deg)):
        n = by.get(nid)
        sf = (n or {}).get("source_file") or ""
        label = (n or {}).get("label") or ""
        if not n or not sf or len(label) < 3 or label in seen:
            continue
        if GENERATED.search(sf) or TESTLIKE.search(sf) or structural[nid] < 2:
            continue
        seen.add(label)
        out.append(label)
        if len(out) >= limit:
            break
    return out


def entry_points(root):
    """Declared entry points from manifests plus shallow main files. Read-only."""
    root = Path(root)
    found = []
    pp = root / "pyproject.toml"
    if pp.is_file():
        m = re.search(r"\[project\.scripts\]\n((?:.+\n)+?)(?:\n|\[|\Z)", pp.read_text(errors="ignore"))
        found += ["script " + ln.strip() for ln in (m.group(1).splitlines() if m else [])][:3]
        # Dotted form under [project]: scripts.name = "pkg.mod:func"
        found += [
            f"script {k} = {v}"
            for k, v in re.findall(r'^scripts\.([\w-]+)\s*=\s*"([^"]+)"', pp.read_text(errors="ignore"), re.M)
        ][:3]
    pj = root / "package.json"
    if pj.is_file():
        try:
            j = json.loads(pj.read_text(errors="ignore"))
            if j.get("bin"):
                found.append("bin " + json.dumps(j["bin"])[:80])
            if j.get("main"):
                found.append("main " + str(j["main"]))
        except ValueError:
            pass
    mains = {"main.go", "main.rs", "__main__.py", "cli.py", "cli.ts", "Main.java"}
    for rel in _walk(root, max_depth=3):
        if os.path.basename(rel) in mains and not (GENERATED.search(rel) or TESTLIKE.search(rel)):
            found.append(rel)
    return found[:6]


def _walk(root, max_depth):
    """Relative file and directory paths up to max_depth, pruning VCS, vendored and dependency trees."""
    root = str(root)
    skip = {".git", "node_modules", "third_party", "vendor", "target", "build", "dist", ".venv", "__pycache__"}
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        depth = 0 if dirpath == root else dirpath[len(root) :].count(os.sep)
        dirnames[:] = sorted(d for d in dirnames if d not in skip) if depth < max_depth else []
        for name in sorted(dirnames) + sorted(filenames):
            out.append(os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/"))
    return out


def arch_docs(root):
    hits = []
    for rel in _walk(root, max_depth=4):
        low = os.path.basename(rel).lower()
        if "architecture" in low or low == "g3doc" or re.match(r".*design.*\.md$", low):
            hits.append(rel)
        if len(hits) >= 3:
            break
    return hits


def readme_text(root):
    for name in ("README.md", "README.rst", "README", "readme.md"):
        p = Path(root) / name
        if p.is_file():
            return p.read_text(errors="ignore")[:6000]
    return ""


def build_entry(graph, repo, sha, branch, repo_root=None):
    nodes, links = graph["nodes"], graph["links"]
    tok = Counter()
    for n in nodes:
        sf = n.get("source_file") or ""
        if GENERATED.search(sf):
            continue
        for t in set(toks(n.get("label", "")) + toks(sf)):
            tok[t] += 1
    readme = readme_text(repo_root) if repo_root else ""
    for t in toks(readme):
        tok[t] += README_WEIGHT
    langs = Counter(os.path.splitext(n.get("source_file") or "")[1] for n in nodes if n.get("source_file"))
    return {
        "repo": repo,
        "sha": sha,
        "branch": branch,
        "built_at": int(time.time()),
        "graphify_version": (graph.get("graph") or {}).get("graphify_version"),
        "nodes": len(nodes),
        "edges": len(links),
        "languages": dict(langs.most_common(5)),
        "hubs": hubs(nodes, links),
        "entry": entry_points(repo_root) if repo_root else [],
        "arch_docs": arch_docs(repo_root) if repo_root else [],
        "summary": " ".join(readme.split())[:240],
        "tok": dict(tok.most_common(MAX_TOKENS)),
    }


def cmd_publish(a):
    store = open_store(a.store)
    repo, sha = _check_name(a.repo, "repo"), _check_name(a.sha, "sha")
    raw = Path(a.graph).read_bytes()
    graph = json.loads(raw)
    if "nodes" not in graph or "links" not in graph:
        raise StoreError("graph file lacks nodes/links; expected graphify node_link JSON")
    rel = f"graphs/{repo}/{sha}/graph.json.gz"
    if store.exists(rel):
        print(f"exists (immutable, not rewritten): {rel}")
    else:
        store.put(rel, gzip.compress(raw, 6))
        print(f"stored {rel} ({len(raw)} -> {store.path(rel).stat().st_size} bytes)")
    entry = build_entry(graph, repo, sha, a.branch, a.repo_root)
    store.put(
        f"graphs/{repo}/latest.json",
        json.dumps({k: entry[k] for k in ("sha", "branch", "built_at", "graphify_version")}).encode(),
    )
    store.put(f"catalog/{repo}.json", json.dumps(entry).encode())
    print(f"catalog/{repo}.json updated (nodes={entry['nodes']} hubs={len(entry['hubs'])})")
    return 0


def load_catalog(store):
    cat = []
    for name in store.list("catalog"):
        if name.endswith(".json"):
            cat.append(json.loads(store.get(f"catalog/{name}")))
    return cat


def _squash(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def name_mentioned(repo, question):
    """True if the repo's name appears as a word, or as 2-3 adjacent words joined ('Google Test' -> googletest)."""
    words = re.findall(r"[a-z0-9]+", question.lower())
    forms = set(words)
    forms.update(a + b for a, b in zip(words, words[1:]))
    forms.update(a + b + c for a, b, c in zip(words, words[1:], words[2:]))
    return _squash(repo) in forms


def rank(cat, question):
    qt = {t for t in toks(question) if t not in QUESTION_FILLER}
    n = len(cat)
    lowered = question.lower()
    scores = {}
    for r in cat:
        s = 0.0
        for t in qt:
            c = r["tok"].get(t, 0)
            if c:
                df = sum(1 for x in cat if t in x["tok"])
                # Squared IDF: words most repos share (generic vocabulary) count far less than rare ones.
                s += math.log(1 + c) * math.log(1 + n / df) ** 2 / math.log(2 + r["nodes"] ** 0.5)
        if name_mentioned(r["repo"], question):
            s += NAME_BOOST
        s += HUB_BOOST * min(2, sum(1 for h in r["hubs"] if len(h) >= 4 and h.lower() in lowered))
        scores[r["repo"]] = s
    return sorted(scores.items(), key=lambda kv: -kv[1])


def decide(ranked, floor, ratio):
    if not ranked or ranked[0][1] < floor:
        return 4
    if len(ranked) > 1 and ranked[1][1] > 0 and ranked[0][1] / ranked[1][1] < ratio:
        return 3
    return 0


def cmd_route(a):
    store = open_store(a.store)
    cat = load_catalog(store)
    if not cat:
        raise StoreError("catalog is empty; publish a graph first")
    ranked = rank(cat, a.question)
    code = decide(ranked, a.floor, a.ratio)
    by = {r["repo"]: r for r in cat}
    show = ranked[:1] if code == 0 else ranked[:3] if code == 3 else []
    result = {
        "outcome": {0: "confident", 3: "ambiguous", 4: "no_match"}[code],
        "candidates": [
            {
                "repo": r,
                "score": round(s, 2),
                "entry": by[r]["entry"],
                "hubs": by[r]["hubs"][:5],
                "arch_docs": by[r]["arch_docs"],
                "summary": by[r]["summary"],
                "sha": by[r]["sha"],
            }
            for r, s in show
        ],
    }
    if code == 4:
        result["indexed_repos"] = sorted(by)
        result["hint"] = "no confident match; name the repo, a symbol, or add scope"
    if a.json:
        print(json.dumps(result, indent=1))
    else:
        print(result["outcome"])
        for c in result["candidates"]:
            print(
                f"  {c['repo']} score={c['score']} entry={c['entry'][:2]} "
                f"hubs={c['hubs'][:3]} docs={c['arch_docs'][:1]}"
            )
        if code == 4:
            print("  indexed:", ", ".join(result["indexed_repos"]))
    return code


def fetch_graph(store, repo, sha, cache):
    repo = _check_name(repo, "repo")
    if not sha:
        sha = json.loads(store.get(f"graphs/{repo}/latest.json"))["sha"]
    sha = _check_name(sha, "sha")
    dest = Path(cache).expanduser() / repo / sha / "graph.json"
    if not dest.is_file():
        data = gzip.decompress(store.get(f"graphs/{repo}/{sha}/graph.json.gz"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=".tmp-")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.chmod(tmp, 0o600)
        os.replace(tmp, dest)
    return dest, sha


def cmd_fetch(a):
    dest, sha = fetch_graph(open_store(a.store), a.repo, a.sha, a.cache)
    print(dest)
    print(f"sha={sha}", file=sys.stderr)
    return 0


def cmd_query(a):
    dest, sha = fetch_graph(open_store(a.store), a.repo, a.sha, a.cache)
    cmd = [a.graphify_bin, a.op, *a.args, "--graph", str(dest)]
    print(f"# {a.repo}@{sha} (graph only; fetch code from your git host at this sha)", file=sys.stderr)
    return subprocess.run(cmd, check=False).returncode


def parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--store", default=os.environ.get("GRAPH_STORE", ".graph-store"), help="store root (env GRAPH_STORE)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("publish", help="store a graph and refresh the repo's catalog entry")
    s.add_argument("--repo", required=True)
    s.add_argument("--sha", required=True)
    s.add_argument("--branch", default="main")
    s.add_argument("--graph", required=True, help="path to graphify-out/graph.json")
    s.add_argument("--repo-root", help="checkout root, for README, manifests and architecture docs")
    s.set_defaults(fn=cmd_publish)
    s = sub.add_parser("route", help="which repo answers this question (exit 0 confident, 3 ambiguous, 4 no match)")
    s.add_argument("question")
    s.add_argument("--floor", type=float, default=DEFAULT_FLOOR, help="min top score (uncalibrated default)")
    s.add_argument("--ratio", type=float, default=DEFAULT_RATIO, help="min top/second score (uncalibrated default)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_route)
    for name, fn, hlp in (
        ("fetch", cmd_fetch, "download a repo's graph to the local cache and print its path"),
        ("query", cmd_query, "run a graphify query against a repo's cached graph"),
    ):
        s = sub.add_parser(name, help=hlp)
        s.add_argument("--repo", required=True)
        s.add_argument("--sha", help="default: latest")
        s.add_argument("--cache", default=os.environ.get("GRAPH_CACHE", "~/.cache/graph-registry"))
        if name == "query":
            s.add_argument("--op", choices=["query", "explain", "affected", "path"], default="query")
            s.add_argument("--graphify-bin", default="graphify")
            s.add_argument("args", nargs="+", help="arguments for the graphify op, e.g. the question")
        s.set_defaults(fn=fn)
    return p


def main(argv=None):
    a = parser().parse_args(argv)
    try:
        return a.fn(a)
    except (StoreError, OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
