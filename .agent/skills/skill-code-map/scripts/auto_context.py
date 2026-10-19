#!/usr/bin/env python3
"""
auto_context.py - Rank the files that matter for a task, using the semantic graph.

Deterministic, no LLM: task words are matched to graph symbols (classes, methods, annotations,
file paths), then expanded along typed edges so the result covers what must change (seeds),
what breaks when they change (dependents) and what they rely on (dependencies).

  auto_context.py "add a field to DataDTO" --src projects/cloud-boot-app/src
  auto_context.py "retry logic in DataService.createData" --graph relationship_graph.json --top 5 --json
"""

import argparse
import importlib.util
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger("auto_context")

# Words that describe the intent of a task, not the code it touches.
STOPWORDS = frozenset(
    "a an the to of in on for and or with from by add adds added fix fixes change changes update updates "
    "remove removes delete create new make use using when where how why what which that this these those "
    "is are be it its into out up down all any new field fields method methods class classes file files "
    "code logic function functions support implement refactor rename move get set".split()
)

SCORE_EXACT = 10  # task names the symbol verbatim (DataDTO, DataService.createData)
SCORE_CASE_INSENSITIVE = 9
SCORE_WORD = 2  # per camelCase word shared between the task and a symbol name
SCORE_ANNOTATION = 3
SCORE_PATH = 1
SCORE_DEPENDENT = 3  # class that uses a seed: breaks when the seed changes
SCORE_DEPENDENCY = 2  # class a seed uses: needed to understand the seed
SCORE_TRANSITIVE = 1  # dependents of dependents
MIN_SEED_SCORE = SCORE_WORD * 2  # one shared word is noise; two words or any exact hit is a seed


def _load_sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, str(Path(__file__).with_name(f"{name}.py")))
    if spec is None or spec.loader is None:
        raise ImportError(f"{name}.py not found next to auto_context.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def split_words(identifier: str) -> List[str]:
    """DataDTO -> [data, dto]; createData -> [create, data]; snake_case and paths split too."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", identifier)
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    return [w.lower() for w in re.split(r"[^A-Za-z0-9]+", spaced) if w]


def task_terms(task: str) -> Tuple[Set[str], Set[str]]:
    """Return (identifiers named verbatim, meaningful lowercase words)."""
    identifiers = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", task))
    identifiers |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_./:-]*[A-Za-z0-9_]", task))
    words = {w for ident in identifiers for w in split_words(ident)}
    return identifiers, {w for w in words if w not in STOPWORDS and len(w) > 1}


class ContextLens:
    def __init__(self, graph: Dict[str, Any]) -> None:
        sq_module = _load_sibling("semantic_query")
        self.query = sq_module.SemanticQuery.from_dict(graph)
        self.nodes: Dict[str, Dict[str, Any]] = self.query.graph.get("nodes", {})
        self.edges: List[Dict[str, Any]] = self.query.graph.get("edges", [])

    def _owner_file(self, owner: str) -> Optional[str]:
        node = self.nodes.get(owner)
        return node.get("file") if node else None

    def seeds(self, task: str) -> Dict[str, Tuple[int, List[str]]]:
        """Score every node against the task; keep owners that clear MIN_SEED_SCORE."""
        identifiers, words = task_terms(task)
        lowered = {i.lower() for i in identifiers}
        annotation_refs = {a.lower() for a in re.findall(r"@([A-Za-z_][A-Za-z0-9_]*)", task)}
        scored: Dict[str, Tuple[int, List[str]]] = {}
        for node_id, node in self.nodes.items():
            score, why = 0, []
            stripped_id = node_id.split(":", 1)[-1] if ":" in node_id else node_id
            if "/" in stripped_id:
                simple = stripped_id.rsplit("/", 1)[-1]
                symbol_words = set(split_words("/".join(stripped_id.split("/")[-2:])))
            else:
                simple = stripped_id.split(".")[-1]
                symbol_words = set(split_words(stripped_id))
            is_method = node.get("type") in ("method", "constructor")
            # A plain lowercase word ("validate") is prose, not a symbol; only treat a bare method name as
            # named when it is camelCase, otherwise require the qualified Class.method form.
            named_simple = simple in identifiers and (not is_method or simple != simple.lower())
            if node_id in identifiers or stripped_id in identifiers or named_simple:
                score, why = SCORE_EXACT, [f"named in task: {node_id}"]
            elif (
                node_id.lower() in lowered
                or stripped_id.lower() in lowered
                or (not is_method and simple.lower() in lowered)
            ):
                score, why = SCORE_CASE_INSENSITIVE, [f"matches symbol (case-insensitive): {node_id}"]
            else:
                shared = words & symbol_words
                if shared:
                    score = SCORE_WORD * len(shared)
                    why = [f"shares words {sorted(shared)} with {node_id}"]

            ann = {a.lower() for a in node.get("annotations", [])}
            written = ann & annotation_refs
            if written:  # "@Transactional" in the task is an explicit structural query
                score = max(score, SCORE_CASE_INSENSITIVE)
                why.append(f"annotated @{sorted(written)[0]}: {node_id}")
            # Annotation/path hints refine an anchored match; they never promote a vague word overlap.
            if score >= SCORE_CASE_INSENSITIVE:
                hit = ann & words
                if hit and not written:
                    score += SCORE_ANNOTATION
                    why.append(f"annotation @{sorted(hit)[0]} on {node_id}")
                if words & set(split_words(str(node.get("file", "")))):
                    score += SCORE_PATH
            if score >= MIN_SEED_SCORE:
                owner = self.query.owner(node_id)
                best = scored.get(owner)
                if best is None or score > best[0]:
                    scored[owner] = (score, why)
        # A verbatim symbol in the task is a precise anchor; word overlap is only a fallback for vague tasks.
        if any(score >= SCORE_CASE_INSENSITIVE for score, _ in scored.values()):
            scored = {o: sw for o, sw in scored.items() if sw[0] >= SCORE_CASE_INSENSITIVE}
        return scored

    def rank(self, task: str, top: int = 10) -> List[Dict[str, Any]]:
        seeds = self.seeds(task)
        if not seeds:
            return []

        by_file: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"score": 0, "reasons": [], "roles": set()})

        def add(owner: str, score: float, role: str, reason: str) -> None:
            file = self._owner_file(owner)
            if not file:
                return
            entry = by_file[file]
            if role == "seed" and "seed" in entry["roles"]:
                # Dampen multi-symbol seed accumulation within the same file
                entry["score"] = max(entry["score"], score) + 1
            else:
                entry["score"] += score
            entry["roles"].add(role)
            if reason not in entry["reasons"]:
                entry["reasons"].append(reason)

        for owner, (score, why) in seeds.items():
            add(owner, score, "seed", why[0])

        # Symmetric 2-hop BFS expansion weighted by edge confidence_score * weight.
        forward: Dict[str, Dict[str, List[Tuple[str, float]]]] = defaultdict(lambda: defaultdict(list))
        reverse: Dict[str, Dict[str, List[Tuple[str, float]]]] = defaultdict(lambda: defaultdict(list))
        for e in self.edges:
            src, dst = self.query.owner(str(e.get("from"))), self.query.owner(str(e.get("to")))
            if src == dst:
                continue
            via = f"{e.get('type')} via {e.get('from')}"
            ew = float(e.get("confidence_score", 1.0)) * float(e.get("weight", 1.0))
            forward[src][dst].append((via, ew))
            reverse[dst][src].append((via, ew))

        first_hop_rev: Set[str] = set()
        first_hop_fwd: Set[str] = set()
        for seed in seeds:
            for dep, vias in reverse.get(seed, {}).items():
                if dep not in seeds:
                    first_hop_rev.add(dep)
                    best_via, best_w = max(vias, key=lambda vw: vw[1])
                    add(dep, round(SCORE_DEPENDENT * best_w, 2), "dependent", f"depends on {seed} ({best_via})")
            for used, vias in forward.get(seed, {}).items():
                if used not in seeds:
                    first_hop_fwd.add(used)
                    best_via, best_w = max(vias, key=lambda vw: vw[1])
                    add(used, round(SCORE_DEPENDENCY * best_w, 2), "dependency", f"used by {seed} ({best_via})")
        for mid in first_hop_rev:
            for dep, vias in reverse.get(mid, {}).items():
                if dep not in seeds and dep not in first_hop_rev:
                    best_via, best_w = max(vias, key=lambda vw: vw[1])
                    add(dep, round(SCORE_TRANSITIVE * best_w, 2), "dependent", f"depends on {mid} ({best_via})")
        for mid in first_hop_fwd:
            for used, vias in forward.get(mid, {}).items():
                if used not in seeds and used not in first_hop_fwd:
                    best_via, best_w = max(vias, key=lambda vw: vw[1])
                    add(used, round(SCORE_TRANSITIVE * best_w, 2), "dependency", f"used by {mid} ({best_via})")

        # Blend Personalized PageRank probability mass into discovered non-seed nodes
        ppr_scores = self.ppr(set(seeds.keys()))
        for owner, mass in ppr_scores.items():
            if owner not in seeds and mass > 0.01:
                file = self._owner_file(owner)
                if file and file in by_file:
                    by_file[file]["score"] = round(by_file[file]["score"] + mass * 2.0, 2)

        ranked = sorted(by_file.items(), key=lambda kv: (-kv[1]["score"], kv[0]))[:top]
        return [
            {
                "file": f,
                "score": int(v["score"]) if float(v["score"]).is_integer() else round(v["score"], 2),
                "roles": sorted(v["roles"]),
                "reasons": v["reasons"],
                "ppr": round(
                    max((ppr_scores.get(o, 0.0) for o in ppr_scores if self._owner_file(o) == f), default=0.0), 4
                ),
            }
            for f, v in ranked
        ]

    def ppr(self, seed_owners: Set[str], alpha: float = 0.85, max_iter: int = 30) -> Dict[str, float]:
        """Degree-normalized Personalized PageRank (biased random walk restarting at seed_owners)."""
        owners: Set[str] = {self.query.owner(nid) for nid in self.nodes}
        for e in self.edges:
            owners.add(self.query.owner(str(e.get("from", ""))))
            owners.add(self.query.owner(str(e.get("to", ""))))
        valid_seeds = {s for s in seed_owners if s in owners} or set(seed_owners)
        if not valid_seeds:
            return {}
        owners |= valid_seeds

        adj: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for e in self.edges:
            u = self.query.owner(str(e.get("from", "")))
            v = self.query.owner(str(e.get("to", "")))
            if u == v or not u or not v:
                continue
            w = float(e.get("confidence_score", 1.0)) * float(e.get("weight", 1.0))
            adj[u][v] += w
            adj[v][u] += w * 0.8

        p: Dict[str, float] = {o: (1.0 / len(valid_seeds) if o in valid_seeds else 0.0) for o in owners}
        restart = dict(p)

        for _ in range(max_iter):
            nxt: Dict[str, float] = {o: (1.0 - alpha) * restart.get(o, 0.0) for o in owners}
            dangling = 0.0
            for u, mass in p.items():
                if not mass:
                    continue
                nbrs = adj.get(u)
                if not nbrs:
                    dangling += mass
                    continue
                total_w = sum(nbrs.values())
                for v, w in nbrs.items():
                    nxt[v] = nxt.get(v, 0.0) + alpha * mass * (w / total_w)
            if dangling:
                share = alpha * dangling / len(valid_seeds)
                for s in valid_seeds:
                    nxt[s] += share
            p = nxt
        return p

    def pack_context(self, task: str, max_tokens: int = 2000) -> Dict[str, Any]:
        """Binary-search token-budget packer over ranked files and their AST symbol signatures."""
        ranked = self.rank(task, top=50)
        if not ranked or max_tokens <= 0:
            return {"packed_text": "", "estimated_tokens": 0, "included_files": []}

        by_file_symbols: Dict[str, List[str]] = defaultdict(list)
        for nid, info in sorted(self.nodes.items()):
            f = info.get("file")
            if f:
                by_file_symbols[f].append(f"  - {info.get('type', 'symbol')} {nid} (L{info.get('line', 1)})")

        def live_summary(f: str) -> List[str]:
            """Compact property summary for virtual k8s:// and vault:// files (no file on disk to read)."""
            out = []
            for nid, info in sorted(self.nodes.items()):
                if info.get("file") != f:
                    continue
                skip = {"file", "line", "type"}
                props = ", ".join(f"{k}={v}" for k, v in sorted(info.items()) if k not in skip and v not in (None, ""))
                out.append(f"  - {info.get('type', 'resource')} {nid}" + (f" ({props})" if props else ""))
            return out[:8]

        def render_k(k: int) -> str:
            if k <= 0:
                return ""
            blocks = []
            for item in ranked[:k]:
                f = item["file"]
                hdr = f"## {f} [score={item['score']}; roles={','.join(item['roles'])}]"
                syms = live_summary(f) if f.startswith(("k8s://", "vault://")) else by_file_symbols.get(f, [])[:8]
                blocks.append("\n".join([hdr] + syms))
            return "\n".join(blocks)

        def est_tokens(txt: str) -> int:
            return max(1, (len(txt) + 3) // 4) if txt else 0

        lo, hi, best_k = 1, len(ranked), 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if est_tokens(render_k(mid)) <= max_tokens:
                best_k = mid
                lo = mid + 1
            else:
                hi = mid - 1

        if best_k == 0:
            return {"packed_text": "", "estimated_tokens": 0, "included_files": []}
        packed_text = render_k(best_k)
        return {
            "packed_text": packed_text,
            "estimated_tokens": est_tokens(packed_text),
            "included_files": [r["file"] for r in ranked[:best_k]],
        }


def load_graph(graph_path: Optional[str], src: Optional[str]) -> Dict[str, Any]:
    if graph_path:
        with open(graph_path, "r", encoding="utf-8") as f:
            return json.load(f)
    builder = _load_sibling("graph_builder").GraphBuilder(src)
    return builder.build_graph()


def format_report(task: str, results: List[Dict[str, Any]]) -> str:
    lines = [f"Task: {task}", f"Relevant files ({len(results)}), ranked:"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['file']}  [score {r['score']}; {', '.join(r['roles'])}]")
        lines.extend(f"     - {reason}" for reason in r["reasons"][:3])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank the files relevant to a task using the semantic graph.")
    parser.add_argument("task", help="Task description; name classes or methods verbatim for best results")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--graph", help="Graph JSON written by graph_builder.py")
    source.add_argument("--src", help="Source directory; the graph is built in memory")
    parser.add_argument("--top", type=int, default=10, help="Maximum files to return (default 10)")
    parser.add_argument("--max-tokens", type=int, default=None, help="Binary-search pack context into token budget")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args()

    for label, value in (("--graph", args.graph), ("--src", args.src)):
        if value and not Path(value).exists():
            logger.error(f"{label} path not found: {value}")
            return 1

    lens = ContextLens(load_graph(args.graph, args.src))
    if args.max_tokens:
        packed = lens.pack_context(args.task, max_tokens=args.max_tokens)
        print(json.dumps(packed, indent=2) if args.json else packed["packed_text"])
        return 0
    results = lens.rank(args.task, args.top)
    if not results:
        logger.error("No graph symbol matches the task. Name a class or method (e.g. DataService.createData).")
        return 2
    print(json.dumps(results, indent=2) if args.json else format_report(args.task, results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
