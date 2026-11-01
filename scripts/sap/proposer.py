#!/usr/bin/env python3
"""
Stage 2: Deterministic Candidate Proposer (SaP §3.2).
Extracts frame tuples (verb, objects, code_langs, linked_scripts) and clusters
procedural units across parents by shared frame and token Jaccard/cosine similarity >= 0.65.
"""

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

ACTION_VERBS = {
    "check",
    "verify",
    "inspect",
    "list",
    "extract",
    "query",
    "scan",
    "audit",
    "build",
    "compile",
    "hydrate",
    "deploy",
    "provision",
    "triage",
    "diagnose",
    "remediate",
    "sync",
    "ingest",
    "consolidate",
    "create",
    "validate",
    "run",
    "execute",
}

DOMAIN_OBJECTS = {
    "pod",
    "pods",
    "cluster",
    "namespace",
    "kubectl",
    "istio",
    "crossplane",
    "composition",
    "xrd",
    "crd",
    "graph",
    "graphify",
    "ast",
    "codemap",
    "drift",
    "vault",
    "terraform",
    "plan",
    "module",
    "aws",
    "iam",
    "vpc",
    "ec2",
    "rds",
    "lambda",
    "sagemaker",
    "gcp",
    "gcloud",
    "logging",
    "monitoring",
    "slo",
    "anomaly",
    "conductor",
    "track",
    "pr",
    "github",
    "branch",
    "memory",
    "sqlite",
    "agent",
    "metadata",
    "mcp",
    "certificate",
    "packer",
    "msbuild",
    "finops",
    "datadog",
    "network",
}

TOKEN_RE = re.compile(r"[a-z0-9_]{3,}")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def extract_frame(unit: dict) -> dict:
    combined = f"{unit.get('heading', '')} {unit.get('text', '')}"
    tokens = tokenize(combined)
    verbs = [t for t in tokens if t in ACTION_VERBS]
    objs = sorted(set(t for t in tokens if t in DOMAIN_OBJECTS))
    primary_verb = verbs[0] if verbs else "execute"
    return {
        "verb": primary_verb,
        "objects": objs[:5],
        "code_langs": unit.get("code_langs", []),
        "linked_scripts": unit.get("linked_scripts", []),
        "tokens": Counter(tokens),
    }


def cosine_sim(c1: Counter, c2: Counter) -> float:
    if not c1 or not c2:
        return 0.0
    common = set(c1.keys()) & set(c2.keys())
    dot = sum(c1[k] * c2[k] for k in common)
    n1 = math.sqrt(sum(v * v for v in c1.values()))
    n2 = math.sqrt(sum(v * v for v in c2.values()))
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return dot / (n1 * n2)


def propose_clusters(parents: list[dict], sim_threshold: float = 0.65) -> list[dict]:
    all_units = []
    for p in parents:
        for u in p.get("procedural_units", []):
            if len(u.get("text", "").strip()) < 20 and not u.get("code_blocks"):
                continue
            u_copy = dict(u)
            u_copy["frame"] = extract_frame(u)
            all_units.append(u_copy)

    visited = set()
    clusters = []
    for i, u1 in enumerate(all_units):
        if i in visited:
            continue
        group = [u1]
        visited.add(i)
        f1 = u1["frame"]
        for j in range(i + 1, len(all_units)):
            if j in visited:
                continue
            u2 = all_units[j]
            f2 = u2["frame"]
            shared_obj = bool(set(f1["objects"]) & set(f2["objects"]))
            shared_script = bool(set(f1["linked_scripts"]) & set(f2["linked_scripts"]))
            sim = cosine_sim(f1["tokens"], f2["tokens"])
            if shared_script or (shared_obj and sim >= sim_threshold):
                group.append(u2)
                visited.add(j)
        if len(group) >= 2:
            parent_set = sorted(set(u["parent"] for u in group))
            clusters.append(
                {
                    "cluster_id": f"cluster_{len(clusters):03d}",
                    "verb": f1["verb"],
                    "objects": f1["objects"],
                    "source_parents": parent_set,
                    "units": [
                        {
                            "unit_id": u["unit_id"],
                            "parent": u["parent"],
                            "heading": u["heading"],
                            "text": u["text"],
                            "code_blocks": u["code_blocks"],
                        }
                        for u in group
                    ],
                }
            )
    return clusters


def main():
    ap = argparse.ArgumentParser(description="SaP Stage 2: Candidate Proposer")
    ap.add_argument("--parents", default=".cache/sap/parents.json", help="Input parents.json")
    ap.add_argument("--out", default=".cache/sap/clusters.json", help="Output clusters.json")
    args = ap.parse_args()

    parents = json.loads(Path(args.parents).read_text(encoding="utf-8"))
    clusters = propose_clusters(parents)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(clusters, indent=2) + "\n", encoding="utf-8")
    print(f"Proposed {len(clusters)} candidate clusters at {out_path}")


if __name__ == "__main__":
    main()
