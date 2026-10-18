#!/usr/bin/env python3
"""Redacted, CRD-aware Kubernetes relationship catalog (skill-code-map).

Read-only. Secret objects are never listed; instances pass an allowlist
projection (`redact`) before they are cached or linked.
"""

import argparse
import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("k8s_catalog")

REDACTED = "[REDACTED]"

# Whole subtrees dropped: payloads, free-form values, last-applied copies.
DROP_KEYS = {"managedFields", "annotations", "data", "binaryData", "stringData", "value", "caBundle"}
# Label-style maps carry selector semantics and are kept as plain str maps.
LABEL_KEYS = {"labels", "matchLabels", "selector", "nodeSelector"}
# Scalars kept as structural: references, identity, topology.
STRUCT_KEYS = {
    "name",
    "namespace",
    "kind",
    "apiVersion",
    "group",
    "version",
    "replicas",
    "port",
    "targetPort",
    "host",
    "path",
    "pathType",
    "type",
    "reason",
    "status",
    "image",
    "protocol",
    "ingressClassName",
    "repoURL",
    "targetRevision",
    "server",
    "project",
    "key",
    "message",
}
REF_SUFFIX = re.compile(r"(Name|Ref|Namespace|Kind)$")
SENSITIVE_KEY = re.compile(r"(?i)(password|passwd|token|credential|api[-_]?key|private|secret|cert|auth)")
URL_CRED = re.compile(r"^(https?://)[^/@\s]+@")


def _leaf(key: str, val: Any) -> Any:
    """Kept value, REDACTED, or None (drop)."""
    if not isinstance(val, (str, int, float, bool)):
        return None
    if isinstance(val, str):
        val = URL_CRED.sub(r"\1", val)
    if REF_SUFFIX.search(key) or key in STRUCT_KEYS:
        return val  # a reference to a secret (tlsSecretName) is structure, not the secret
    if SENSITIVE_KEY.search(key):
        return REDACTED
    return None


def _project(obj: Any, key: str = "") -> Any:
    if isinstance(obj, dict):
        if key in LABEL_KEYS:
            return {str(k): v for k, v in obj.items() if isinstance(v, (str, int, bool))}
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if k in DROP_KEYS:
                continue
            p = _project(v, k) if isinstance(v, (dict, list)) else _leaf(k, v)
            if p not in (None, {}, []):
                out[k] = p
        return out
    if isinstance(obj, list):
        items = [_project(v, key) if isinstance(v, (dict, list)) else _leaf(key, v) for v in obj]
        return [i for i in items if i not in (None, {}, [])]
    return None


PEM = re.compile(r"-----BEGIN [A-Z ]+-----")
JWT = re.compile(r"^eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*$")
B64 = re.compile(r"^[A-Za-z0-9+/]{40,}={0,2}$")
HEX = re.compile(r"^[0-9a-fA-F]+$")


def scan_for_secrets(obj: Any, _key: str = "", _path: str = "$") -> List[str]:
    """Paths of values that still look like secrets; empty list means clean."""
    if isinstance(obj, dict):
        return [h for k, v in obj.items() for h in scan_for_secrets(v, str(k), f"{_path}.{k}")]
    if isinstance(obj, list):
        return [h for i, v in enumerate(obj) for h in scan_for_secrets(v, _key, f"{_path}[{i}]")]
    if isinstance(obj, str) and (PEM.search(obj) or JWT.match(obj) or (B64.match(obj) and not HEX.match(obj))):
        return [_path]  # pure-hex strings are content hashes (composition-hash, digests), not credentials
    is_ref = bool(REF_SUFFIX.search(_key)) or _key in STRUCT_KEYS
    if obj not in (None, REDACTED, "") and SENSITIVE_KEY.search(_key) and not is_ref:
        return [_path]
    return []


def redact(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Allowlist projection of one Kubernetes object. Secrets keep identity only."""
    md = obj.get("metadata", {}) or {}
    meta: Dict[str, Any] = {"name": md.get("name", "")}
    if md.get("namespace"):
        meta["namespace"] = md["namespace"]
    out: Dict[str, Any] = {"apiVersion": obj.get("apiVersion", ""), "kind": obj.get("kind", ""), "metadata": meta}
    if obj.get("kind") == "Secret":
        if obj.get("type"):
            out["type"] = obj["type"]
        return out
    if md.get("labels"):
        meta["labels"] = _project(md["labels"], "labels")
    owners = [{k: o[k] for k in ("apiVersion", "kind", "name") if k in o} for o in md.get("ownerReferences") or []]
    if owners:
        meta["ownerReferences"] = owners
    if "spec" in obj:
        out["spec"] = _project(obj["spec"], "spec")
    cond = (obj.get("status") or {}).get("conditions")
    if cond:
        out["status"] = {"conditions": _project(cond, "conditions")}
    return out


# ---------------------------------------------------------------- identity / OpenAPI

REF_FIELD = re.compile(r"(Ref|Refs|RefSelector|Selector)$")
REF_FIELD_EXACT = {"ownerReferences", "selector", "resourceRefs", "compositeTypeRef", "secretKeyRef", "secretName"}


def gk(api_version: str, kind: str) -> str:
    """Version-independent node key: group/Kind (core group is 'core')."""
    group = api_version.rsplit("/", 1)[0] if "/" in api_version else "core"
    return f"{group}/{kind}"


def _resolve(doc: Dict[str, Any], ref: str) -> Dict[str, Any]:
    cur: Any = doc
    for part in ref.lstrip("#/").split("/"):
        cur = cur.get(part, {})
    return cur


def _ref_fields(
    doc: Dict[str, Any], schema: Dict[str, Any], prefix: str = "", depth: int = 0, seen: frozenset = frozenset()
) -> List[str]:
    if depth > 6:
        return []
    if "$ref" in schema:
        r = schema["$ref"]
        return [] if r in seen else _ref_fields(doc, _resolve(doc, r), prefix, depth + 1, seen | {r})
    found: List[str] = []
    for name, sub in (schema.get("properties") or {}).items():
        if name == "metadata":
            continue
        path = f"{prefix}.{name}" if prefix else name
        if REF_FIELD.search(name) or name in REF_FIELD_EXACT:
            found.append(path)
        else:
            found += _ref_fields(doc, sub, path, depth + 1, seen)
    for key in ("items", "additionalProperties"):
        if isinstance(schema.get(key), dict):
            found += _ref_fields(doc, schema[key], prefix, depth + 1, seen)
    return found


def parse_openapi_v3(doc: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Map 'group/Kind' to {versions, ref_fields} from one /openapi/v3 group-version doc."""
    out: Dict[str, Dict[str, Any]] = {}
    for schema in (doc.get("components", {}).get("schemas", {}) or {}).values():
        for g in schema.get("x-kubernetes-group-version-kind", []) or []:
            e = out.setdefault(f"{g.get('group') or 'core'}/{g['kind']}", {"versions": [], "ref_fields": []})
            if g["version"] not in e["versions"]:
                e["versions"].append(g["version"])
            e["ref_fields"] = sorted(set(e["ref_fields"]) | set(_ref_fields(doc, schema)))
    return out


def merge_catalogs(parts: Iterable[Dict[str, Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for part in parts:
        for key, e in part.items():
            m = merged.setdefault(key, {"versions": [], "ref_fields": []})
            m["versions"] = sorted(set(m["versions"]) | set(e.get("versions", [])))
            m["ref_fields"] = sorted(set(m["ref_fields"]) | set(e.get("ref_fields", [])))
    return merged


def apply_crd_overlay(catalog: Dict[str, Dict[str, Any]], crds: Dict[str, Any]) -> None:
    """Add scope, plural, storage version and served versions from CRD objects."""
    for item in crds.get("items", []):
        spec = item.get("spec", {})
        e = catalog.setdefault(
            f"{spec.get('group', '')}/{spec.get('names', {}).get('kind', '')}", {"versions": [], "ref_fields": []}
        )
        e.update(scope=spec.get("scope"), plural=spec.get("names", {}).get("plural"), crd=True)
        vers = spec.get("versions", [])
        e["versions"] = sorted(set(e["versions"]) | {v["name"] for v in vers if v.get("served")})
        for v in vers:
            if v.get("storage"):
                e["storage_version"] = v["name"]


# ------------------------------------------------------------------ edges

WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job", "Pod"}
CLUSTER_SCOPED_KINDS = {
    "Namespace",
    "Node",
    "PersistentVolume",
    "StorageClass",
    "ClusterRole",
    "ClusterRoleBinding",
    "CustomResourceDefinition",
    "Composition",
    "CompositeResourceDefinition",
}


def node_id(api_version: str, kind: str, namespace: str, name: str) -> str:
    return f"{gk(api_version, kind)}/{namespace or ''}/{name}"


def _walk(obj: Any) -> Iterator[Tuple[str, Any]]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def build_edges(objs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Relationship edges from already-redacted objects. Node key is group/Kind/namespace/name."""
    edges: List[Dict[str, str]] = []
    seen: Set[Tuple[str, str, str]] = set()

    def add(frm: str, typ: str, to: str) -> None:
        if (frm, typ, to) not in seen:
            seen.add((frm, typ, to))
            edges.append({"from": frm, "to": to, "type": typ})

    workloads = []
    for o in objs:
        md, spec = o["metadata"], o.get("spec", {})
        labels = spec.get("template", {}).get("metadata", {}).get("labels") or md.get("labels") or {}
        if o["kind"] in WORKLOAD_KINDS and labels:
            ns = md.get("namespace", "")
            workloads.append((node_id(o["apiVersion"], o["kind"], ns, md["name"]), ns, labels))

    for o in objs:
        md, spec, kind = o["metadata"], o.get("spec", {}), o["kind"]
        ns = md.get("namespace", "")
        me = node_id(o["apiVersion"], kind, ns, md["name"])

        for ow in md.get("ownerReferences", []):
            ow_ns = "" if ow.get("kind") in CLUSTER_SCOPED_KINDS else ns
            add(me, "owned-by", node_id(ow["apiVersion"], ow["kind"], ow_ns, ow["name"]))

        if kind == "Service" and spec.get("selector"):
            for wid, wns, labels in workloads:
                if wns == ns and all(labels.get(k) == v for k, v in spec["selector"].items()):
                    add(me, "selects", wid)

        for k, v in _walk(spec):
            if kind == "Ingress" and k == "service" and isinstance(v, dict) and v.get("name"):
                add(me, "routes-to", node_id("v1", "Service", ns, v["name"]))
            elif (
                k in ("secretKeyRef", "secretRef", "writeConnectionSecretToRef")
                and isinstance(v, dict)
                and v.get("name")
            ):
                add(me, "references-secret", node_id("v1", "Secret", v.get("namespace") or ns, v["name"]))
            elif k in ("secretName", "tlsSecretName") and isinstance(v, str):
                add(me, "references-secret", node_id("v1", "Secret", ns, v))
            elif k == "resourceRefs" and isinstance(v, list):
                for r in v:
                    if r.get("kind") and r.get("name"):
                        r_ns = r.get("namespace") or ("" if r["kind"] in CLUSTER_SCOPED_KINDS else ns)
                        add(me, "composes", node_id(r.get("apiVersion", "v1"), r["kind"], r_ns, r["name"]))
            elif k == "compositionRef" and isinstance(v, dict) and v.get("name"):
                add(me, "uses-composition", node_id("apiextensions.crossplane.io/v1", "Composition", "", v["name"]))
            elif k == "compositeTypeRef" and isinstance(v, dict) and v.get("kind"):
                add(me, "composes-type", f"kind:{gk(v.get('apiVersion', ''), v['kind'])}")

        if kind == "Application" and o["apiVersion"].startswith("argoproj.io"):
            if spec.get("destination", {}).get("namespace"):
                add(me, "deploys-to", node_id("v1", "Namespace", "", spec["destination"]["namespace"]))
            if spec.get("source", {}).get("repoURL"):
                add(me, "sources-from", f"repo:{spec['source']['repoURL']}")
    return edges


# ------------------------------------------------------------------ cache


class SecretLeakError(RuntimeError):
    pass


def write_cache(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON at mode 0600; refuse (and write nothing) if a secret-shaped value survives."""
    leaks = scan_for_secrets(data)
    if leaks:
        raise SecretLeakError(f"refusing to write cache; secret-shaped values at: {leaks[:5]}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
    os.replace(tmp, path)


# ---------------------------------------------------------- cluster I/O

# Never listed: credentials, and kinds whose payload is arbitrary user data.
NEVER_LIST = {"secrets", "configmaps", "tokenreviews", "tokenrequests", "serviceaccounts/token"}
DEFAULT_GROUPS = [
    "core",
    "apps",
    "networking.k8s.io",
    "policy",
    "autoscaling",
    "crossplane.io",
    "database.example.org",
    "argoproj.io",
    "acid.zalan.do",
]


def check_prod_context(context: Optional[str], allow_prod_read: bool = False) -> None:
    if context and "prod" in context.lower() and not allow_prod_read:
        raise SystemExit(
            f"refusing: kubectl context '{context}' looks like production; pass --allow-prod-read for read-only access"
        )


def _ctx_args(context: Optional[str] = None, kubeconfig: Optional[str] = None) -> List[str]:
    out: List[str] = []
    if context:
        out.extend(["--context", context])
    if kubeconfig:
        out.extend(["--kubeconfig", kubeconfig])
    return out


def _kubectl(*args: str) -> Optional[str]:
    res = subprocess.run(["kubectl", *args], capture_output=True, text=True)
    if res.returncode != 0:
        logger.warning("kubectl %s failed: %s", " ".join(args[:3]), res.stderr.strip()[:200])
        return None
    return res.stdout


def _raw_json(path: str, extra: Sequence[str] = ()) -> Optional[Dict[str, Any]]:
    out = _kubectl(*extra, "get", "--raw", path)
    return json.loads(out) if out else None


def _group_of(resource: str) -> str:
    return resource.split(".", 1)[1] if "." in resource else "core"


def _wanted(group: str, groups: List[str]) -> bool:
    return not groups or any(group == g or group.endswith("." + g) for g in groups)


def collect(
    groups: List[str],
    namespaces: List[str],
    context: Optional[str] = None,
    kubeconfig: Optional[str] = None,
) -> Dict[str, Any]:
    """Catalog (OpenAPI v3 + CRDs) plus redacted instances and edges. Read-only."""
    extra = _ctx_args(context, kubeconfig)
    index = _raw_json("/openapi/v3", extra) or {"paths": {}}
    parts = []
    for rel, meta in index["paths"].items():
        if rel.startswith(("api/", "apis/")):
            doc = _raw_json(meta["serverRelativeURL"], extra)
            if doc:
                parts.append(parse_openapi_v3(doc))
    catalog = merge_catalogs(parts)
    apply_crd_overlay(
        catalog,
        _raw_json("/apis/apiextensions.k8s.io/v1/customresourcedefinitions", extra) or {"items": []},
    )

    inventory = (_kubectl(*extra, "api-resources", "--verbs=list", "-o", "name") or "").split()
    objs: List[Dict[str, Any]] = []
    for res in inventory:
        if res.split(".")[0] in NEVER_LIST or not _wanted(_group_of(res), groups):
            continue
        out = _kubectl(*extra, "get", res, "-A", "-o", "json", "--ignore-not-found")
        for item in json.loads(out).get("items", []) if out else []:
            ns = item.get("metadata", {}).get("namespace")
            if ns and namespaces and ns not in namespaces:
                continue
            objs.append(redact(item))
    nodes = {
        node_id(o["apiVersion"], o["kind"], o["metadata"].get("namespace", ""), o["metadata"]["name"]): o for o in objs
    }
    return {
        "catalog": catalog,
        "nodes": nodes,
        "edges": build_edges(objs),
        "stats": {"kinds": len(catalog), "objects": len(objs)},
    }


def canonical_graphify_id(raw_id: str) -> str:
    """Convert k8s_catalog node_id (group/Kind/ns/name) into canonical k8s:<group>/<Kind>/<ns_or__cluster_>/<name>."""
    if raw_id.startswith(("k8s:", "kind:", "repo:", "vault:")):
        return raw_id
    parts = raw_id.split("/")
    if len(parts) == 4:
        group, kind, ns, name = parts
        return f"k8s:{group}/{kind}/{ns or '_cluster_'}/{name}"
    return f"k8s:{raw_id}"


def to_graphify(cat_graph: Dict[str, Any]) -> Dict[str, Any]:
    """Convert k8s_catalog graph into standard Graphify node_link_data schema with canonical k8s: IDs."""
    catalog = cat_graph.get("catalog", {})
    g_nodes = []
    for nid, obj in cat_graph.get("nodes", {}).items():
        kind = obj.get("kind", "")
        api = obj.get("apiVersion", "v1")
        md = obj.get("metadata", {})
        ns = md.get("namespace", "")
        name = md.get("name", nid)
        g_key = gk(api, kind)
        cat_info = catalog.get(g_key, {})
        cid = canonical_graphify_id(nid)
        g_nodes.append(
            {
                "id": cid,
                "label": f"{kind}: {name}",
                "file_type": "k8s_resource",
                "source_file": f"k8s://{ns or 'cluster'}/{kind.lower()}/{name}",
                "source_location": "k8s-api",
                "community": 11 if cat_info.get("crd") else 10,
                "_origin": "k8s_catalog",
                "properties": {
                    "kind": kind,
                    "apiVersion": api,
                    "namespace": ns or None,
                    "name": name,
                    "crd": bool(cat_info.get("crd")),
                    "served_versions": cat_info.get("versions", []),
                    "ref_fields": cat_info.get("ref_fields", []),
                },
            }
        )
    g_links = [
        {
            "source": canonical_graphify_id(e["from"]),
            "target": canonical_graphify_id(e["to"]),
            "relation": e["type"],
            "_origin": "k8s_catalog",
            "confidence": "EXTRACTED",
            "confidence_score": 1.0,
            "weight": 1.0,
        }
        for e in cat_graph.get("edges", [])
    ]
    return {
        "directed": True,
        "multigraph": False,
        "graph": {
            "name": "k8s-crd-catalog-graph",
            "source": "k8s-openapi-v3",
            "node_count": len(g_nodes),
            "edge_count": len(g_links),
        },
        "nodes": g_nodes,
        "links": g_links,
        "hyperedges": [],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a redacted CRD-aware Kubernetes relationship cache.")
    ap.add_argument("--output", default="projects/cloud-boot-app/.cache/k8s-graph/k8s_graph.json")
    ap.add_argument(
        "--groups", nargs="*", default=DEFAULT_GROUPS, help="API group suffixes to fetch instances for; empty = all"
    )
    ap.add_argument("--namespaces", nargs="*", default=["cloud-boot-app", "default", "argocd", "crossplane-system"])
    ap.add_argument("--context", default=None, help="kubectl context")
    ap.add_argument("--kubeconfig", default=None, help="Path to kubeconfig")
    ap.add_argument("--allow-prod-read", action="store_true", help="Permit read-only access to a *prod* context")
    ap.add_argument("--format", choices=("catalog", "graphify"), default="catalog", help="Output schema format")
    args = ap.parse_args()
    ctx = args.context or (_kubectl(*_ctx_args(None, args.kubeconfig), "config", "current-context") or "").strip()
    check_prod_context(ctx, allow_prod_read=args.allow_prod_read)
    graph = collect(args.groups, args.namespaces, context=args.context, kubeconfig=args.kubeconfig)
    out_data = to_graphify(graph) if args.format == "graphify" else graph
    write_cache(Path(args.output), out_data)
    logger.info("wrote %s (%s): %s", args.output, args.format, graph["stats"])


if __name__ == "__main__":
    main()
