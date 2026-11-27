#!/usr/bin/env python3
"""Read-only GCP Cloud Asset Inventory (CAI) catalog & Graphify topology builder.

Queries `gcloud asset list --content-type=resource` (with full `resource.data`
payloads) and `search-all-iam-policies`, redacts sensitive fields, walks
resource URI references across Compute/GKE/KMS/IAM/Fleet, and emits Graphify JSON.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("gcp_catalog")

REDACTED = "[REDACTED]"
DROP_KEYS = {"payload", "secret", "privateKey", "token", "password", "credentials", "value"}
SKIP_WALK_KEYS = {"selfLink", "selfLinkWithId", "region", "zone", "kind", "id", "creationTimestamp"}
_PROJ_SUFFIX_RE = re.compile(r"(?:projects|folders|organizations)/[^/]+/(.+)$")


def _short_name(full_name: str) -> str:
    return full_name.rstrip("/").rsplit("/", 1)[-1] if full_name else "unknown"


def _suffix_key(uri_or_name: str) -> str:
    """Normalize //host/projects/p/a/b or https://.../projects/p/a/b -> a/b."""
    m = _PROJ_SUFFIX_RE.search(uri_or_name.rstrip("/"))
    return m.group(1) if m else ""


def canonical_gcp_id(asset_type: str, full_name: str, display_name: str = "") -> str:
    """Produce stable Graphify node ID: gcp:<assetType>/<shortName>."""
    short = display_name or _short_name(full_name)
    return f"gcp:{asset_type}/{short}"


def redact_asset(obj: Any) -> Any:
    """Recursively drop sensitive keys while preserving structural metadata."""
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if k in DROP_KEYS or any(tok in k.lower() for tok in ("secret", "password", "token", "privatekey")):
                if k in ("kmsKey", "kmsKeyName", "secretVersionSelectionPolicy", "serviceAccount"):
                    out[k] = redact_asset(v)
                else:
                    continue
            else:
                out[k] = redact_asset(v)
        return out
    if isinstance(obj, list):
        return [redact_asset(item) for item in obj]
    return obj


def _run_gcloud(args: Sequence[str]) -> Any:
    cmd = ["gcloud", *args, "--format=json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout or "[]")


def fetch_cai_resources(project_id: str, asset_types: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch full CAI resource payloads via `gcloud asset list --content-type=resource`."""
    args = ["asset", "list", f"--project={project_id}", "--content-type=resource"]
    if asset_types:
        args.append(f"--asset-types={asset_types}")
    return _run_gcloud(args)


def fetch_cai_iam_policies(project_id: str) -> List[Dict[str, Any]]:
    return _run_gcloud(["asset", "search-all-iam-policies", f"--scope=projects/{project_id}"])


def _relation_for_key(key: str) -> str:
    kl = key.lower()
    if "network" in kl and "sub" not in kl:
        return "uses-network"
    if "subnetwork" in kl or "subnet" in kl:
        return "uses-subnet"
    if "kms" in kl or "cryptokey" in kl:
        return "encrypted-by-kms"
    if "serviceaccount" in kl:
        return "uses-service-account"
    if "router" in kl:
        return "uses-router"
    if "cluster" in kl:
        return "targets-cluster"
    if kl in ("target", "targetpool", "backendservice", "instancegroup", "urlmap", "membership"):
        return "targets"
    return "references"


def _walk_data_refs(obj: Any, parent_key: str = "") -> Iterable[Tuple[str, str]]:
    """Recursively yield (relation, uri_or_email) from resource.data / additionalAttributes."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in SKIP_WALK_KEYS:
                continue
            if isinstance(v, str):
                if ("googleapis.com/" in v or v.startswith("projects/") or v.startswith("//")) and (
                    "/locations/" in v or "/regions/" in v or "/global/" in v
                ):
                    yield _relation_for_key(k), v
                elif k.lower() in ("serviceaccount", "email") and v.endswith(".gserviceaccount.com"):
                    yield "uses-service-account", v
            elif isinstance(v, (dict, list)):
                yield from _walk_data_refs(v, parent_key=k)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, str):
                if "googleapis.com/" in item or item.startswith("projects/") or item.startswith("//"):
                    yield _relation_for_key(parent_key), item
                elif item.endswith(".gserviceaccount.com"):
                    yield "uses-service-account", item
            elif isinstance(item, (dict, list)):
                yield from _walk_data_refs(item, parent_key=parent_key)


def build_graphify(
    assets: Sequence[Dict[str, Any]],
    iam_policies: Sequence[Dict[str, Any]] | None = None,
    project_id: str = "",
) -> Dict[str, Any]:
    """Convert CAI resources + IAM policies into a Graphify-compatible graph dict."""
    nodes_by_id: Dict[str, Dict[str, Any]] = {}
    ref_to_id: Dict[str, str] = {}
    edges: List[Dict[str, Any]] = []
    seen_edges: set[Tuple[str, str, str]] = set()

    def ensure_node(
        node_id: str,
        label: str,
        asset_type: str,
        location: str = "global",
        full_name: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if node_id not in nodes_by_id:
            props: Dict[str, Any] = {
                "assetType": asset_type,
                "location": location,
                "status": "Active",
            }
            if full_name:
                props["fullResourceName"] = full_name
            if extra:
                props.update(extra)
            nodes_by_id[node_id] = {
                "id": node_id,
                "label": label,
                "type": "gcp_resource",
                "source_file": f"gcp://{project_id or 'project'}/{asset_type}/{label}",
                "properties": props,
            }

    def add_edge(src: str, rel: str, tgt: str) -> None:
        key = (src, rel, tgt)
        if src and tgt and src != tgt and key not in seen_edges:
            seen_edges.add(key)
            edges.append({"source": src, "relation": rel, "target": tgt, "confidence": "EXTRACTED"})

    # Pass 1: Register all asset nodes and index by full name, project-relative path, and suffix
    sanitized_assets = [redact_asset(a) for a in assets]
    for asset in sanitized_assets:
        full_name = asset.get("name", "")
        asset_type = asset.get("assetType", "gcp.Resource")
        res_block = asset.get("resource") or {}
        res_data = res_block.get("data") if isinstance(res_block, dict) else {}
        display_name = (
            asset.get("displayName")
            or (res_data.get("name") if isinstance(res_data, dict) else "")
            or _short_name(full_name)
        )
        location = asset.get("location") or (res_block.get("location") if isinstance(res_block, dict) else "") or "global"
        nid = canonical_gcp_id(asset_type, full_name, display_name)
        extra: Dict[str, Any] = {}
        if isinstance(res_data, dict) and isinstance(res_data.get("description"), str) and "kubernetes.io/service-name" in res_data["description"]:
            extra["k8s_service_hint"] = res_data["description"]
        ensure_node(nid, display_name, asset_type, location=location, full_name=full_name, extra=extra)
        if full_name:
            ref_to_id[full_name] = nid
            suffix = _suffix_key(full_name)
            if suffix:
                ref_to_id.setdefault(suffix, nid)
        if asset_type == "iam.googleapis.com/ServiceAccount" and isinstance(res_data, dict) and res_data.get("email"):
            ref_to_id[res_data["email"]] = nid

    # Pass 2: Structural & resource.data dependency edges
    for asset in sanitized_assets:
        full_name = asset.get("name", "")
        asset_type = asset.get("assetType", "gcp.Resource")
        res_block = asset.get("resource") or {}
        res_data = res_block.get("data") if isinstance(res_block, dict) else {}
        display_name = (
            asset.get("displayName")
            or (res_data.get("name") if isinstance(res_data, dict) else "")
            or _short_name(full_name)
        )
        nid = canonical_gcp_id(asset_type, full_name, display_name)

        parent = asset.get("parentFullResourceName") or (res_block.get("parent") if isinstance(res_block, dict) else "") or ""
        if parent:
            ptgt = ref_to_id.get(parent) or ref_to_id.get(_suffix_key(parent))
            if ptgt:
                add_edge(ptgt, "contains", nid)

        kms_key = asset.get("kmsKey", "") or asset.get("kmsKeyName", "")
        if kms_key:
            tgt = ref_to_id.get(kms_key) or ref_to_id.get(_suffix_key(kms_key)) or canonical_gcp_id("cloudkms.googleapis.com/CryptoKey", kms_key)
            if tgt not in nodes_by_id:
                ensure_node(tgt, _short_name(kms_key), "cloudkms.googleapis.com/CryptoKey", full_name=kms_key)
            add_edge(nid, "encrypted-by-kms", tgt)

        for source_dict in (asset.get("additionalAttributes") or {}, res_data if isinstance(res_data, dict) else {}):
            if isinstance(source_dict, dict):
                for rel, ref in _walk_data_refs(source_dict):
                    tgt = ref_to_id.get(ref) or ref_to_id.get(_suffix_key(ref))
                    if not tgt and ref.endswith(".gserviceaccount.com"):
                        tgt = canonical_gcp_id("iam.googleapis.com/ServiceAccount", ref, ref)
                        ensure_node(tgt, ref, "iam.googleapis.com/ServiceAccount", full_name=ref)
                    if tgt:
                        add_edge(nid, rel, tgt)

    # Pass 3: IAM policy bindings
    for entry in iam_policies or []:
        res = entry.get("resource", "")
        res_type = entry.get("assetType", "gcp.Resource")
        res_id = ref_to_id.get(res) or ref_to_id.get(_suffix_key(res)) or canonical_gcp_id(res_type, res)
        if res_id not in nodes_by_id:
            ensure_node(res_id, _short_name(res), res_type, full_name=res)
        for binding in (entry.get("policy") or {}).get("bindings", []):
            role = binding.get("role", "")
            for member in binding.get("members", []):
                mem_id = f"gcp:iam/Member/{member}"
                ensure_node(mem_id, member, "iam/Member", extra={"role": role})
                add_edge(mem_id, "grants-iam-role", res_id)

    return {
        "directed": True,
        "multigraph": False,
        "graph": {"source": "gcp_catalog", "project_id": project_id, "evidence_boundary": "live gcp cai"},
        "nodes": list(nodes_by_id.values()),
        "links": edges,
    }


def merge_with_graphify(gcp_graph: Dict[str, Any], base_path: Path) -> Dict[str, Any]:
    """Merge GCP CAI graph into an existing Graphify JSON and bridge GCP -> K8s/TF nodes."""
    base = json.loads(base_path.read_text(encoding="utf-8"))
    existing_nodes = {n["id"]: n for n in base.get("nodes", [])}
    for node in gcp_graph.get("nodes", []):
        existing_nodes.setdefault(node["id"], node)

    links = list(base.get("links", []))
    seen = {(e["source"], e["relation"], e["target"]) for e in links}
    for e in gcp_graph.get("links", []):
        k = (e["source"], e["relation"], e["target"])
        if k not in seen:
            seen.add(k)
            links.append(e)

    # Cross-layer bridges: ForwardingRule k8s_service_hint -> K8s Service, IAM SA -> K8s SA
    k8s_nodes = [n for n in existing_nodes.values() if n.get("type") == "k8s_resource"]
    gcp_nodes = [n for n in existing_nodes.values() if n.get("type") == "gcp_resource"]

    for gn in gcp_nodes:
        props = gn.get("properties", {})
        atype = props.get("assetType", "")
        hint = props.get("k8s_service_hint", "")
        if hint:
            try:
                svc_ref = json.loads(hint).get("kubernetes.io/service-name", "")
                if "/" in svc_ref:
                    ns, name = svc_ref.split("/", 1)
                    k8s_id = f"k8s:core/Service/{ns}/{name}"
                    if k8s_id in existing_nodes:
                        k = (gn["id"], "routes-to-k8s-service", k8s_id)
                        if k not in seen:
                            seen.add(k)
                            links.append({"source": gn["id"], "relation": "routes-to-k8s-service", "target": k8s_id, "confidence": "EXTRACTED"})
            except json.JSONDecodeError:
                pass
        if atype == "iam.googleapis.com/ServiceAccount" and "eso-wi" in gn.get("label", ""):
            for kn in k8s_nodes:
                if kn["id"].endswith("/ServiceAccount/external-secrets/external-secrets"):
                    k = (kn["id"], "workload-identity-bound", gn["id"])
                    if k not in seen:
                        seen.add(k)
                        links.append({"source": kn["id"], "relation": "workload-identity-bound", "target": gn["id"], "confidence": "INFERRED"})

    return {
        "directed": True,
        "multigraph": False,
        "graph": base.get("graph", {}),
        "nodes": list(existing_nodes.values()),
        "links": links,
    }


def write_graph_atomic(path: Path, payload: Dict[str, Any]) -> None:
    """Write JSON atomically with 0600 permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".gcp_catalog_", suffix=".tmp", dir=str(path.parent))
    try:
        os.chmod(tmp_name, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="GCP Cloud Asset Inventory catalog & Graphify builder")
    parser.add_argument("--project", required=True, help="Target GCP Project ID")
    parser.add_argument("--asset-types", default=None, help="Comma-separated CAI asset types filter")
    parser.add_argument("--include-iam", action="store_true", help="Include search-all-iam-policies bindings")
    parser.add_argument("--input", type=Path, default=None, help="Offline CAI resources JSON file")
    parser.add_argument("--iam-input", type=Path, default=None, help="Offline CAI IAM policies JSON file")
    parser.add_argument("--merge-with", type=Path, default=None, help="Merge into existing Graphify JSON")
    parser.add_argument("--format", choices=("graphify", "markdown"), default="graphify")
    parser.add_argument("--out", type=Path, default=None, help="Output file path (0600 atomic write)")
    args = parser.parse_args(argv)

    assets = json.loads(args.input.read_text(encoding="utf-8")) if args.input else fetch_cai_resources(args.project, args.asset_types)
    iam_policies = (
        json.loads(args.iam_input.read_text(encoding="utf-8"))
        if args.iam_input
        else (fetch_cai_iam_policies(args.project) if args.include_iam else [])
    )

    graph = build_graphify(assets, iam_policies, project_id=args.project)
    if args.merge_with:
        graph = merge_with_graphify(graph, args.merge_with)

    if args.format == "markdown":
        lines = [f"# GCP Asset Catalog ({args.project})", f"- Nodes: {len(graph['nodes'])}", f"- Edges: {len(graph['links'])}", ""]
        for n in sorted(graph["nodes"], key=lambda x: x["id"])[:60]:
            lines.append(f"- `{n['id']}` ({n.get('properties', {}).get('location', 'global')})")
        output_text = "\n".join(lines)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(output_text, encoding="utf-8")
        else:
            print(output_text)
        return 0

    if args.out:
        write_graph_atomic(args.out, graph)
        logger.info("Wrote %d nodes and %d links (0600) to %s", len(graph["nodes"]), len(graph["links"]), args.out)
    else:
        print(json.dumps(graph, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
