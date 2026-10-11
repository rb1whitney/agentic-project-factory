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
    words = {w for ident in identifiers for w in split_words(ident)}
    return identifiers, {w for w in words if w not in STOPWORDS and len(w) > 1}


class ContextLens:
    def __init__(self, graph: Dict[str, Any]) -> None:
        sq_module = _load_sibling("semantic_query")
        self.query = sq_module.SemanticQuery.from_dict(graph)
        self.nodes: Dict[str, Dict[str, Any]] = graph.get("nodes", {})
        self.edges: List[Dict[str, Any]] = graph.get("edges", [])

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
            simple = node_id.split(".")[-1]
            is_method = node.get("type") in ("method", "constructor")
            # A plain lowercase word ("validate") is prose, not a symbol; only treat a bare method name as
            # named when it is camelCase, otherwise require the qualified Class.method form.
            named_simple = simple in identifiers and (not is_method or simple != simple.lower())
            if node_id in identifiers or named_simple:
                score, why = SCORE_EXACT, [f"named in task: {node_id}"]
            elif node_id.lower() in lowered or (not is_method and simple.lower() in lowered):
                score, why = SCORE_CASE_INSENSITIVE, [f"matches symbol (case-insensitive): {node_id}"]
            else:
                shared = words & set(split_words(simple))
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

        def add(owner: str, score: int, role: str, reason: str) -> None:
            file = self._owner_file(owner)
            if not file:
                return
            entry = by_file[file]
            entry["score"] += score
            entry["roles"].add(role)
            if reason not in entry["reasons"]:
                entry["reasons"].append(reason)

        for owner, (score, why) in seeds.items():
            add(owner, score, "seed", why[0])

        # One typed hop in each direction, then a second hop of dependents.
        forward: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        reverse: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        for e in self.edges:
            src, dst = self.query.owner(str(e.get("from"))), self.query.owner(str(e.get("to")))
            if src == dst:
                continue
            via = f"{e.get('type')} via {e.get('from')}"
            forward[src][dst].append(via)
            reverse[dst][src].append(via)

        first_hop: Set[str] = set()
        for seed in seeds:
            for dep, vias in reverse.get(seed, {}).items():
                if dep not in seeds:
                    first_hop.add(dep)
                    add(dep, SCORE_DEPENDENT, "dependent", f"depends on {seed} ({vias[0]})")
            for used, vias in forward.get(seed, {}).items():
                if used not in seeds:
                    add(used, SCORE_DEPENDENCY, "dependency", f"used by {seed} ({vias[0]})")
        for mid in first_hop:
            for dep, vias in reverse.get(mid, {}).items():
                if dep not in seeds and dep not in first_hop:
                    add(dep, SCORE_TRANSITIVE, "dependent", f"depends on {mid} ({vias[0]})")

        ranked = sorted(by_file.items(), key=lambda kv: (-kv[1]["score"], kv[0]))[:top]
        return [
            {"file": f, "score": v["score"], "roles": sorted(v["roles"]), "reasons": v["reasons"]}
            for f, v in ranked
        ]


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
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args()

    for label, value in (("--graph", args.graph), ("--src", args.src)):
        if value and not Path(value).exists():
            logger.error(f"{label} path not found: {value}")
            return 1

    results = ContextLens(load_graph(args.graph, args.src)).rank(args.task, args.top)
    if not results:
        logger.error("No graph symbol matches the task. Name a class or method (e.g. DataService.createData).")
        return 2
    print(json.dumps(results, indent=2) if args.json else format_report(args.task, results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
