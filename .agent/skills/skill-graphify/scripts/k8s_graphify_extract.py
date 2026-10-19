#!/usr/bin/env python3
"""
k8s_graphify_extract.py
Extracts Kubernetes cluster state, CRDs, and live workload relationships into
the standard Graphify knowledge graph format (graph.json).

Enforces strict zero-leak redaction:
- Drops secret contents, managedFields, and last-applied-configuration
- Strips literal env values while preserving secret/configmap references
- Replaces credential leaf keys and url passwords with [REDACTED]
- Generates Graphify nodes, links, and hyperedges
"""

import argparse
import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

REDACTED = "[REDACTED]"

SENSITIVE_KEY_PATTERN = re.compile(r"(?i)(password|passwd|token|apikey|api_key|secret|credential|private_?key|auth)")
BASE64_PATTERN = re.compile(r"^[A-Za-z0-9+/]{40,}={0,2}$")
HEX_HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{40,64}$")
PEM_PATTERN = re.compile(r"-----BEGIN [A-Z ]+KEY-----")
JWT_PATTERN = re.compile(r"^eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$")
URL_CREDS_PATTERN = re.compile(r"(https?://)([^:]+):([^@]+)@")


def sanitize_url(url: str) -> str:
    """Removes user:pass credentials from URLs."""
    return URL_CREDS_PATTERN.sub(r"\1", url)


def redact(val: Any, parent_key: str = "") -> Any:
    """
    Recursively redacts sensitive keys, env literal strings, secrets, and auth URLs.
    """
    if isinstance(val, dict):
        kind = val.get("kind")
        # Special handling for Secret objects: never keep secret data/stringData
        if kind == "Secret":
            meta = val.get("metadata", {})
            clean_meta = {
                "name": meta.get("name"),
                "namespace": meta.get("namespace"),
                "labels": meta.get("labels", {}),
                "creationTimestamp": meta.get("creationTimestamp"),
            }
            return {
                "apiVersion": val.get("apiVersion", "v1"),
                "kind": "Secret",
                "type": val.get("type", "Opaque"),
                "metadata": {k: v for k, v in clean_meta.items() if v is not None},
            }

        res = {}
        for k, v in val.items():
            # Strip Kubernetes internal metadata that leaks secrets or bloats context
            if k in ("managedFields", "kubectl.kubernetes.io/last-applied-configuration"):
                continue

            # Strip annotations with last-applied
            if k == "annotations" and isinstance(v, dict):
                v = {ak: av for ak, av in v.items() if "last-applied-configuration" not in ak}

            # Check if key is sensitive leaf
            if SENSITIVE_KEY_PATTERN.search(k) and not isinstance(v, (dict, list)):
                # Keep reference names like secretRef, secretName, tlsSecretName intact
                if k.endswith("Ref") or k.endswith("Name"):
                    res[k] = v
                else:
                    res[k] = REDACTED
                continue

            # Redact env arrays: drop literal values, retain secretKeyRef/configMapKeyRef
            if k == "env" and isinstance(v, list):
                clean_env = []
                for env_item in v:
                    if isinstance(env_item, dict):
                        clean_item = {"name": env_item.get("name")}
                        if "valueFrom" in env_item:
                            clean_item["valueFrom"] = redact(env_item["valueFrom"])
                        clean_env.append(clean_item)
                res[k] = clean_env
                continue

            res[k] = redact(v, k)
        return res

    elif isinstance(val, list):
        return [redact(item, parent_key) for item in val]

    elif isinstance(val, (str, int, float, bool)):
        if parent_key and SENSITIVE_KEY_PATTERN.search(parent_key):
            if not (parent_key.endswith("Ref") or parent_key.endswith("Name")):
                return REDACTED
        if isinstance(val, str) and URL_CREDS_PATTERN.search(val):
            return sanitize_url(val)
        return val

    return val


def scan_for_secrets(val: Any, path: str = "", parent_key: str = "") -> List[str]:
    """
    Scans data structure for any surviving sensitive values or unredacted secrets.
    """
    leaks = []
    if isinstance(val, dict):
        for k, v in val.items():
            cur_path = f"{path}.{k}" if path else k
            if SENSITIVE_KEY_PATTERN.search(k) and not isinstance(v, (dict, list)):
                if not (k.endswith("Ref") or k.endswith("Name")) and v != REDACTED:
                    leaks.append(f"Sensitive key '{cur_path}' contains live value")
            leaks.extend(scan_for_secrets(v, cur_path, k))
    elif isinstance(val, list):
        for idx, item in enumerate(val):
            leaks.extend(scan_for_secrets(item, f"{path}[{idx}]", parent_key))
    elif isinstance(val, str):
        if val == REDACTED:
            return []
        if (
            parent_key
            and SENSITIVE_KEY_PATTERN.search(parent_key)
            and not (parent_key.endswith("Ref") or parent_key.endswith("Name"))
        ):
            leaks.append(f"Sensitive key '{path}' contains live value")
        elif PEM_PATTERN.search(val):
            leaks.append(f"PEM certificate/key detected at '{path}'")
        elif JWT_PATTERN.match(val):
            leaks.append(f"JWT token detected at '{path}'")
        elif (
            len(val) >= 40
            and BASE64_PATTERN.match(val)
            and not HEX_HASH_PATTERN.match(val)
            and not val.startswith(("sha256:", "sha384:", "sha512:"))
        ):
            leaks.append(f"High-entropy Base64 string detected at '{path}'")
    return leaks


def get_default_kubeconfig() -> Optional[str]:
    env_kube = os.environ.get("KUBECONFIG")
    if env_kube and os.path.exists(env_kube) and os.access(env_kube, os.R_OK):
        return env_kube
    candidates = [
        os.path.expanduser("~/.kube/k3s.yaml"),
        os.path.expanduser("~/.kube/config"),
    ]
    for c in candidates:
        if os.path.exists(c) and os.access(c, os.R_OK):
            return c
    return None


def run_kubectl(
    args: List[str],
    kubeconfig: Optional[str] = None,
    context: Optional[str] = None,
) -> Any:
    kpath = kubeconfig or get_default_kubeconfig()
    env = os.environ.copy()
    if kpath:
        env["KUBECONFIG"] = kpath

    cmd = ["kubectl"] + (["--context", context] if context else []) + args
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    if res.returncode != 0:
        return None
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return res.stdout.strip()


# One definition of the cluster-safety constants and guards lives in skill-code-map's k8s_catalog.
# Redaction is deliberately NOT shared: the two extractors use different, separately tested policies.
_CATALOG_DIR = Path(__file__).resolve().parents[2] / "skill-code-map" / "scripts"
if str(_CATALOG_DIR) not in sys.path:
    sys.path.insert(0, str(_CATALOG_DIR))
from k8s_catalog import (  # noqa: E402
    CLUSTER_SCOPED_KINDS,
    NEVER_LIST,
    WORKLOAD_KINDS,
    SecretLeakError,
    check_prod_context,
    discover_catalog,
)


def write_graph_atomic(path: Path, data: Dict[str, Any]) -> None:
    """Writes graph JSON atomically with mode 0600 after verifying zero secret leaks."""
    leaks = scan_for_secrets(data)
    if leaks:
        raise SecretLeakError(f"refusing to write graph; secret-shaped values at: {leaks[:5]}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)


def _walk_spec(obj: Any):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from _walk_spec(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_spec(v)


BATCH_SIZE = 12
REQUEST_TIMEOUT = "--request-timeout=15s"


def _filter_api_names(out: Any) -> List[str]:
    if not isinstance(out, str):
        return []
    return [r.strip() for r in out.splitlines() if r.strip() and r.strip().split(".")[0] not in NEVER_LIST]


def plan_queries(
    namespaced: List[str],
    cluster_scoped: List[str],
    namespace: Optional[str],
    all_namespaces: bool,
    batch_size: int = BATCH_SIZE,
) -> List[List[str]]:
    """Builds `kubectl get` argv lists: namespaced kinds batched with -n/-A, cluster-scoped kinds batched bare.

    Scoping with -n at the API server (instead of -A then filtering in Python) avoids cluster-wide lists."""
    scope = ["-A"] if (all_namespaces or not namespace) else ["-n", namespace]
    queries: List[List[str]] = []
    for names, args in ((namespaced, scope), (cluster_scoped, [])):
        for i in range(0, len(names), batch_size):
            chunk = ",".join(names[i : i + batch_size])
            queries.append(["get", chunk] + args + ["-o", "json", "--ignore-not-found", REQUEST_TIMEOUT])
    return queries


def _run_batch(q: List[str], kubeconfig: Optional[str], context: Optional[str]) -> List[Any]:
    """Runs one batched get; on failure (one forbidden/unknown kind fails the whole call) retries per kind."""
    data = run_kubectl(q, kubeconfig, context=context)
    if isinstance(data, dict):
        return [data]
    kinds = q[1].split(",")
    if len(kinds) == 1:
        return []
    return [d for k in kinds for d in _run_batch([q[0], k] + q[2:], kubeconfig, context)]


def fetch_cluster_resources(
    namespace: Optional[str] = "cloud-boot-app",
    all_namespaces: bool = False,
    kubeconfig: Optional[str] = None,
    dynamic_discovery: bool = True,
    context: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetches core and CRD resources via dynamic api-resources discovery with static fallback."""
    raw_objects: List[Dict[str, Any]] = []
    ns_args = ["-A"] if (all_namespaces or not namespace) else ["-n", namespace]

    queries: List[List[str]] = []
    if dynamic_discovery:
        base = ["api-resources", "--verbs=list", "-o", "name"]
        namespaced = _filter_api_names(run_kubectl(base + ["--namespaced=true"], kubeconfig, context=context))
        cluster_scoped = _filter_api_names(run_kubectl(base + ["--namespaced=false"], kubeconfig, context=context))
        queries = plan_queries(namespaced, cluster_scoped, namespace, all_namespaces)

    if not queries:
        queries = [
            ["get", "all"] + ns_args + ["-o", "json"],
            ["get", "ingress,pvc,serviceaccount"] + ns_args + ["-o", "json"],
            ["get", "postgresql.acid.zalan.do"] + ns_args + ["-o", "json"],
            ["get", "cloudbootapps.database.example.org", "-A", "-o", "json"],
            ["get", "xcloudbootapps.database.example.org", "-A", "-o", "json"],
            ["get", "compositions.apiextensions.crossplane.io", "-o", "json"],
            ["get", "applications.argoproj.io", "-A", "-o", "json"],
        ]

    for q in queries:
        for data in _run_batch(q, kubeconfig, context):
            if data.get("kind") == "List":
                for item in data.get("items", []):
                    item_ns = item.get("metadata", {}).get("namespace")
                    if not all_namespaces and namespace and item_ns and item_ns != namespace:
                        if item.get("kind") not in ("Application", "CloudBootApp"):
                            continue
                    raw_objects.append(item)
            elif "kind" in data and "metadata" in data:
                raw_objects.append(data)

    clean_objects = []
    for obj in raw_objects:
        redacted_obj = redact(obj)
        leaks = scan_for_secrets(redacted_obj)
        if leaks:
            print(f"Warning: Redaction scan flagged object {redacted_obj.get('kind')}: {leaks}", file=sys.stderr)
            continue
        clean_objects.append(redacted_obj)

    return clean_objects


def canonical_node_id(api_version: str, kind: str, namespace: Optional[str], name: str) -> str:
    group = "core"
    if "/" in api_version:
        group = api_version.split("/")[0]
    ns = namespace if namespace else "_cluster_"
    return f"k8s:{group}/{kind}/{ns}/{name}"


def labels_match(selector: Dict[str, str], labels: Dict[str, str]) -> bool:
    if not selector or not labels:
        return False
    return all(labels.get(k) == v for k, v in selector.items())


def build_graphify_k8s_graph(objects: List[Dict[str, Any]], repo_dir: Optional[str] = None) -> Dict[str, Any]:
    nodes: Dict[str, Dict[str, Any]] = {}
    links: List[Dict[str, Any]] = []
    seen_links: Set[Tuple[str, str, str]] = set()

    def add_link(src: str, rel: str, tgt: str, weight: float = 1.0):
        key = (src, rel, tgt)
        if key not in seen_links:
            seen_links.add(key)
            links.append(
                {
                    "source": src,
                    "target": tgt,
                    "relation": rel,
                    "_origin": "k8s_api",
                    "confidence": "EXTRACTED",
                    "confidence_score": 1.0,
                    "weight": weight,
                }
            )

    diagnostics: List[Dict[str, Any]] = []
    # Kinds we list: absence from the fetched state means the target is genuinely missing.
    LISTED_KINDS = {"ServiceAccount", "Role", "ClusterRole", "Composition", "Service", "PersistentVolumeClaim"}
    # Kinds NEVER_LIST blocks: existence is unknown, never claim missing.
    REDACTED_KINDS = {"Secret", "ConfigMap"}

    def ensure_phantom_node(
        nid: str, kind: str, ns: Optional[str], name: str, community: int = 10, referrer: Optional[str] = None
    ) -> None:
        if nid in nodes:
            return
        if kind in LISTED_KINDS:
            status = "MISSING_TARGET"
            diagnostics.append(
                {"code": "missing-target", "severity": "error", "node": nid, "referrer": referrer,
                 "message": f"{kind} {ns + '/' if ns else ''}{name} is referenced but not present"}
            )
        elif kind in REDACTED_KINDS:
            status = "Unverified (Redacted Kind)"
        else:
            status = "Referenced"
        nodes[nid] = {
            "id": nid,
            "label": f"{kind}: {name}",
            "file_type": "k8s_resource",
            "source_file": f"k8s://{ns or 'cluster'}/{kind.lower()}/{name}",
            "source_location": "k8s-api",
            "community": community,
            "_origin": "k8s_api",
            "properties": {"kind": kind, "namespace": ns, "name": name, "status": status},
        }

    deployments = []
    services = []
    ingresses = []
    workloads = []
    argocd_apps = []
    postgres_clusters = []

    for obj in objects:
        api_version = obj.get("apiVersion", "v1")
        kind = obj.get("kind", "")
        meta = obj.get("metadata", {})
        name = meta.get("name", "")
        ns = meta.get("namespace")

        node_id = canonical_node_id(api_version, kind, ns, name)

        community = 10
        if (
            "crossplane" in api_version
            or kind in ("CloudBootApp", "XCloudBootApp", "Composition")
            or kind.startswith("X")
        ):
            community = 11
        elif "acid.zalan.do" in api_version:
            community = 12
        elif "argoproj.io" in api_version:
            community = 13
        elif kind in ("Service", "Ingress"):
            community = 14
        elif kind in WORKLOAD_KINDS:
            community = 15

        status = obj.get("status", {})
        status_summary = "Active"
        pod_extra: Dict[str, Any] = {}
        if kind == "Pod":
            phase = status.get("phase", "Unknown")
            container_statuses = status.get("containerStatuses", [])
            waiting_reasons = [
                cs.get("state", {}).get("waiting", {}).get("reason")
                for cs in container_statuses
                if cs.get("state", {}).get("waiting")
            ]
            if waiting_reasons:
                status_summary = f"{phase} ({', '.join(filter(None, waiting_reasons))})"
            else:
                status_summary = phase
            pod_extra = {
                "containers_ready": f"{sum(1 for c in container_statuses if c.get('ready'))}/{len(container_statuses)}",
                "restart_count": sum(int(c.get("restartCount", 0)) for c in container_statuses),
            }
            init_statuses = status.get("initContainerStatuses") or []
            if init_statuses:
                done = all((c.get("state") or {}).get("terminated", {}).get("exitCode") == 0 for c in init_statuses)
                pod_extra["init"] = "ok" if done else "pending"
        elif "conditions" in status:
            conds = status.get("conditions", [])
            for c in conds:
                if c.get("type") in ("Ready", "Synced") and c.get("status") == "False":
                    status_summary = f"Degraded ({c.get('reason', 'Unready')})"

        nodes[node_id] = {
            "id": node_id,
            "label": f"{kind}: {name}",
            "file_type": "k8s_resource",
            "source_file": f"k8s://{ns or 'cluster'}/{kind.lower()}/{name}",
            "source_location": "k8s-api",
            "community": community,
            "_origin": "k8s_api",
            "properties": {
                "kind": kind,
                "apiVersion": api_version,
                "namespace": ns,
                "name": name,
                "status": status_summary,
                **pod_extra,
            },
        }

        if kind == "Deployment":
            deployments.append(obj)
        elif kind == "Service":
            services.append(obj)
        elif kind == "Ingress":
            ingresses.append(obj)
        elif kind == "Application":
            argocd_apps.append(obj)
        elif kind == "postgresql":
            postgres_clusters.append(obj)

        if kind in WORKLOAD_KINDS:
            workloads.append(obj)

    # 1. Ingress -> Service routing
    for ing in ingresses:
        ing_id = canonical_node_id(
            ing["apiVersion"], ing["kind"], ing["metadata"].get("namespace"), ing["metadata"]["name"]
        )
        rules = ing.get("spec", {}).get("rules", [])
        for rule in rules:
            for path in rule.get("http", {}).get("paths", []):
                svc_name = path.get("backend", {}).get("service", {}).get("name")
                if svc_name:
                    svc_id = canonical_node_id("v1", "Service", ing["metadata"].get("namespace"), svc_name)
                    if svc_id in nodes:
                        add_link(ing_id, "routes-to", svc_id)

    # 2. Service -> any Workload (Deployment / StatefulSet / DaemonSet / Pod / Job) selection
    for svc in services:
        svc_meta = svc.get("metadata", {})
        svc_ns = svc_meta.get("namespace")
        svc_name = svc_meta.get("name")
        svc_id = canonical_node_id(svc["apiVersion"], svc["kind"], svc_ns, svc_name)
        selector = svc.get("spec", {}).get("selector", {})
        if selector:
            for wl in workloads:
                if wl.get("metadata", {}).get("namespace") == svc_ns:
                    tmpl_labels = wl.get("spec", {}).get("template", {}).get("metadata", {}).get("labels") or wl.get(
                        "metadata", {}
                    ).get("labels", {})
                    if labels_match(selector, tmpl_labels):
                        wl_id = canonical_node_id(wl["apiVersion"], wl["kind"], svc_ns, wl["metadata"]["name"])
                        add_link(svc_id, "selects", wl_id)

    # 3. Generic ownerReferences, Crossplane refs, Secret refs across all objects
    for obj in objects:
        meta = obj.get("metadata", {})
        ns = meta.get("namespace")
        name = meta.get("name", "")
        kind = obj.get("kind", "")
        spec = obj.get("spec", {}) or {}
        src_id = canonical_node_id(obj.get("apiVersion", "v1"), kind, ns, name)

        for owner in meta.get("ownerReferences", []):
            owner_ns = None if owner.get("kind") in CLUSTER_SCOPED_KINDS else ns
            owner_id = canonical_node_id(
                owner.get("apiVersion", "v1"), owner.get("kind", ""), owner_ns, owner.get("name", "")
            )
            if owner_id in nodes:
                add_link(owner_id, "manages", src_id)

        # Crossplane Claim -> XR
        res_ref = spec.get("resourceRef")
        if isinstance(res_ref, dict) and res_ref.get("name"):
            xr_id = canonical_node_id(
                res_ref.get("apiVersion", obj.get("apiVersion", "v1")),
                res_ref.get("kind", "XCloudBootApp"),
                None,
                res_ref["name"],
            )
            if xr_id in nodes:
                add_link(src_id, "binds-xr", xr_id)

        # Generic spec walk for compositionRef, resourceRefs, compositeTypeRef, and secret references
        for k, v in _walk_spec(spec):
            if k == "compositionRef" and isinstance(v, dict) and v.get("name"):
                comp_name = v["name"]
                comp_id = canonical_node_id("apiextensions.crossplane.io/v1", "Composition", None, comp_name)
                ensure_phantom_node(comp_id, "Composition", None, comp_name, community=11, referrer=src_id)
                add_link(src_id, "uses-composition", comp_id)
            elif k == "resourceRefs" and isinstance(v, list):
                for r in v:
                    if isinstance(r, dict) and r.get("kind") and r.get("name"):
                        r_ns = r.get("namespace") or (None if r["kind"] in CLUSTER_SCOPED_KINDS else ns)
                        target_id = canonical_node_id(r.get("apiVersion", "v1"), r["kind"], r_ns, r["name"])
                        add_link(src_id, "composes", target_id)
            elif k == "compositeTypeRef" and isinstance(v, dict) and v.get("kind"):
                add_link(src_id, "composes-type", f"kind:{v.get('apiVersion', '')}/{v['kind']}")
            elif (
                k in ("secretKeyRef", "secretRef", "writeConnectionSecretToRef")
                and isinstance(v, dict)
                and v.get("name")
            ):
                sec_ns = v.get("namespace") or ns or "default"
                sec_id = canonical_node_id("v1", "Secret", sec_ns, v["name"])
                ensure_phantom_node(sec_id, "Secret", sec_ns, v["name"], community=10, referrer=src_id)
                add_link(src_id, "references-secret", sec_id)
            elif k in ("secretName", "tlsSecretName") and isinstance(v, str) and v != REDACTED:
                sec_ns = ns or "default"
                sec_id = canonical_node_id("v1", "Secret", sec_ns, v)
                ensure_phantom_node(sec_id, "Secret", sec_ns, v, community=10, referrer=src_id)
                add_link(src_id, "references-secret", sec_id)

    # 4. Postgres CRD -> StatefulSet / Service
    for pg in postgres_clusters:
        pg_meta = pg.get("metadata", {})
        pg_ns = pg_meta.get("namespace")
        pg_name = pg_meta.get("name")
        pg_id = canonical_node_id(pg["apiVersion"], pg["kind"], pg_ns, pg_name)

        sts_id = canonical_node_id("apps/v1", "StatefulSet", pg_ns, pg_name)
        if sts_id in nodes:
            add_link(pg_id, "provisions", sts_id)

        svc_id = canonical_node_id("v1", "Service", pg_ns, pg_name)
        if svc_id in nodes:
            add_link(pg_id, "exposes-as", svc_id)

    # 5. ArgoCD Application -> Target Namespace / Repo
    for app in argocd_apps:
        app_meta = app.get("metadata", {})
        app_name = app_meta.get("name")
        app_ns = app_meta.get("namespace")
        app_id = canonical_node_id(app["apiVersion"], app["kind"], app_ns, app_name)

        dest_ns = app.get("spec", {}).get("destination", {}).get("namespace")
        if dest_ns:
            ns_id = canonical_node_id("v1", "Namespace", None, dest_ns)
            ensure_phantom_node(ns_id, "Namespace", None, dest_ns, community=13)
            add_link(app_id, "deploys-to", ns_id)

        repo_url = app.get("spec", {}).get("source", {}).get("repoURL")
        if repo_url:
            repo_id = f"repo:{repo_url}"
            ensure_phantom_node(repo_id, "GitRepository", None, repo_url, community=13)
            add_link(app_id, "sources-from", repo_id)

    # 6. Workload -> DB reference and ServiceAccount binding
    for wl in workloads:
        wl_meta = wl.get("metadata", {})
        wl_ns = wl_meta.get("namespace")
        wl_id = canonical_node_id(wl["apiVersion"], wl["kind"], wl_ns, wl_meta.get("name", ""))
        spec = wl.get("spec", {}) or {}
        sa_name = spec.get("template", {}).get("spec", {}).get("serviceAccountName") or spec.get("serviceAccountName")
        if sa_name:
            sa_id = canonical_node_id("v1", "ServiceAccount", wl_ns or "default", sa_name)
            ensure_phantom_node(sa_id, "ServiceAccount", wl_ns or "default", sa_name, community=10, referrer=wl_id)
            add_link(wl_id, "uses-serviceaccount", sa_id)

    # 6b. Service -> Endpoints/EndpointSlice -> Pod (routes-to-pod), with ready/not-ready counts
    for obj in objects:
        if obj.get("kind") != "Endpoints":
            continue
        em = obj.get("metadata", {})
        ens = em.get("namespace")
        svc_id = canonical_node_id("v1", "Service", ens, em.get("name", ""))
        if svc_id not in nodes:
            continue
        ready = notready = 0
        for sub in obj.get("subsets") or []:
            for addr_key in ("addresses", "notReadyAddresses"):
                for addr in sub.get(addr_key) or []:
                    if addr_key == "addresses":
                        ready += 1
                    else:
                        notready += 1
                    ref = addr.get("targetRef") or {}
                    if ref.get("kind") == "Pod" and ref.get("name"):
                        pod_id = canonical_node_id("v1", "Pod", ref.get("namespace") or ens, ref["name"])
                        if pod_id in nodes:
                            add_link(svc_id, "routes-to-pod", pod_id)
        nodes[svc_id]["properties"]["endpoints_ready"] = ready
        nodes[svc_id]["properties"]["endpoints_not_ready"] = notready
        if ready == 0:
            diagnostics.append(
                {"code": "service-no-ready-endpoints", "severity": "warning", "node": svc_id, "referrer": None,
                 "message": f"Service has 0 ready endpoints ({notready} not ready)"}
            )

    # 6c. Workload -> ConfigMap / PVC mounts and envFrom
    for wl in workloads:
        wl_meta = wl.get("metadata", {})
        wl_ns = wl_meta.get("namespace")
        wl_id = canonical_node_id(wl["apiVersion"], wl["kind"], wl_ns, wl_meta.get("name", ""))
        pod_spec = (wl.get("spec", {}).get("template", {}).get("spec") if wl["kind"] != "Pod" else wl.get("spec")) or {}
        for vol in pod_spec.get("volumes") or []:
            cm = (vol.get("configMap") or {}).get("name")
            pvc = (vol.get("persistentVolumeClaim") or {}).get("claimName")
            if cm:
                cm_id = canonical_node_id("v1", "ConfigMap", wl_ns, cm)
                ensure_phantom_node(cm_id, "ConfigMap", wl_ns, cm, community=10, referrer=wl_id)
                add_link(wl_id, "mounts-configmap", cm_id)
            if pvc:
                pvc_id = canonical_node_id("v1", "PersistentVolumeClaim", wl_ns, pvc)
                ensure_phantom_node(pvc_id, "PersistentVolumeClaim", wl_ns, pvc, community=10, referrer=wl_id)
                add_link(wl_id, "mounts-pvc", pvc_id)
        for ctr in (pod_spec.get("containers") or []) + (pod_spec.get("initContainers") or []):
            for ef in ctr.get("envFrom") or []:
                cm = (ef.get("configMapRef") or {}).get("name")
                if cm:
                    cm_id = canonical_node_id("v1", "ConfigMap", wl_ns, cm)
                    ensure_phantom_node(cm_id, "ConfigMap", wl_ns, cm, community=10, referrer=wl_id)
                    add_link(wl_id, "mounts-configmap", cm_id)

    # 6d. Admission webhook configs -> backing Service (intercepts-workloads)
    for obj in objects:
        if obj.get("kind") not in ("MutatingWebhookConfiguration", "ValidatingWebhookConfiguration"):
            continue
        wm = obj.get("metadata", {})
        wh_id = canonical_node_id(obj.get("apiVersion", "v1"), obj["kind"], None, wm.get("name", ""))
        for hook in obj.get("webhooks") or []:
            svc = (hook.get("clientConfig") or {}).get("service") or {}
            if svc.get("name"):
                svc_id = canonical_node_id("v1", "Service", svc.get("namespace"), svc["name"])
                ensure_phantom_node(svc_id, "Service", svc.get("namespace"), svc["name"], community=14, referrer=wh_id)
                add_link(wh_id, "intercepts-workloads", svc_id)

    # 6e. Service mesh / Gateway API -> Service
    for obj in objects:
        kind = obj.get("kind", "")
        om = obj.get("metadata", {})
        ons = om.get("namespace")
        spec = obj.get("spec", {}) or {}
        if kind not in ("VirtualService", "DestinationRule", "HTTPRoute"):
            continue
        src = canonical_node_id(obj.get("apiVersion", "v1"), kind, ons, om.get("name", ""))
        targets: List[Tuple[str, str]] = []  # (service name, namespace)
        if kind == "DestinationRule" and spec.get("host"):
            targets.append((str(spec["host"]), ons or ""))
            rel = "applies-mtls-policy" if (spec.get("trafficPolicy") or {}).get("tls") else "mesh-routes-to"
        elif kind == "VirtualService":
            rel = "mesh-routes-to"
            for http in spec.get("http") or []:
                for route in http.get("route") or []:
                    if (route.get("destination") or {}).get("host"):
                        targets.append((str(route["destination"]["host"]), ons or ""))
        else:
            rel = "mesh-routes-to"
            for rule in spec.get("rules") or []:
                for ref in rule.get("backendRefs") or []:
                    if ref.get("name"):
                        targets.append((str(ref["name"]), ref.get("namespace") or ons or ""))
        for host, tns in targets:
            parts = host.split(".")  # 'svc', 'svc.ns', 'svc.ns.svc.cluster.local'
            sname, sns = parts[0], (parts[1] if len(parts) > 1 else tns)
            svc_id = canonical_node_id("v1", "Service", sns or None, sname)
            if svc_id in nodes:
                add_link(src, rel, svc_id)

    # 7. RBAC RoleBinding / ClusterRoleBinding -> Role/ClusterRole & ServiceAccount
    for obj in objects:
        kind = obj.get("kind", "")
        if kind not in ("RoleBinding", "ClusterRoleBinding"):
            continue
        meta = obj.get("metadata", {})
        ns = meta.get("namespace")
        rb_id = canonical_node_id(obj.get("apiVersion", "rbac.authorization.k8s.io/v1"), kind, ns, meta.get("name", ""))
        role_ref = obj.get("roleRef") or {}
        if role_ref.get("name") and role_ref.get("kind"):
            r_kind = role_ref["kind"]
            r_ns = None if r_kind == "ClusterRole" else ns
            r_api = role_ref.get("apiGroup") or "rbac.authorization.k8s.io"
            r_id = canonical_node_id(f"{r_api}/v1", r_kind, r_ns, role_ref["name"])
            ensure_phantom_node(r_id, r_kind, r_ns, role_ref["name"], community=10, referrer=rb_id)
            add_link(rb_id, "grants-role", r_id)
        for subj in obj.get("subjects") or []:
            if isinstance(subj, dict) and subj.get("kind") == "ServiceAccount" and subj.get("name"):
                s_ns = subj.get("namespace") or ns or "default"
                sa_id = canonical_node_id("v1", "ServiceAccount", s_ns, subj["name"])
                ensure_phantom_node(sa_id, "ServiceAccount", s_ns, subj["name"], community=10, referrer=rb_id)
                add_link(rb_id, "binds-subject", sa_id)

    # 8. NetworkPolicy -> Workload isolation and ingress reachability
    for obj in objects:
        if obj.get("kind") != "NetworkPolicy":
            continue
        np_meta = obj.get("metadata", {})
        np_ns = np_meta.get("namespace")
        np_id = canonical_node_id(
            obj.get("apiVersion", "networking.k8s.io/v1"), "NetworkPolicy", np_ns, np_meta.get("name", "")
        )
        spec = obj.get("spec", {}) or {}
        raw_pod_sel = spec.get("podSelector")
        pod_sel = (raw_pod_sel or {}).get("matchLabels") if isinstance(raw_pod_sel, dict) else None
        isolated_wls: List[str] = []
        for wl in workloads:
            if wl.get("metadata", {}).get("namespace") != np_ns:
                continue
            w_labels = (
                wl.get("spec", {}).get("template", {}).get("metadata", {}).get("labels")
                or wl.get("metadata", {}).get("labels")
                or {}
            )
            # In Kubernetes NetworkPolicy, an empty podSelector ({}) selects all pods in the namespace
            if isinstance(raw_pod_sel, dict) and (not pod_sel or labels_match(pod_sel, w_labels)):
                wid = canonical_node_id(wl["apiVersion"], wl["kind"], np_ns, wl["metadata"]["name"])
                isolated_wls.append(wid)
                add_link(np_id, "isolates-workload", wid)
        for ing_rule in spec.get("ingress") or []:
            for frm in ing_rule.get("from") or []:
                if not isinstance(frm, dict) or "podSelector" not in frm:
                    continue
                raw_from_sel = frm.get("podSelector")
                from_sel = (raw_from_sel or {}).get("matchLabels") if isinstance(raw_from_sel, dict) else None
                for wl in workloads:
                    if wl.get("metadata", {}).get("namespace") != np_ns:
                        continue
                    w_labels = (
                        wl.get("spec", {}).get("template", {}).get("metadata", {}).get("labels")
                        or wl.get("metadata", {}).get("labels")
                        or {}
                    )
                    if isinstance(raw_from_sel, dict) and (not from_sel or labels_match(from_sel, w_labels)):
                        src_wid = canonical_node_id(wl["apiVersion"], wl["kind"], np_ns, wl["metadata"]["name"])
                        for dst_wid in isolated_wls:
                            if src_wid != dst_wid:
                                add_link(src_wid, "allowed-by-netpol", dst_wid)

    return {
        "directed": True,
        "multigraph": False,
        "graph": {
            "name": "kubernetes-cluster-knowledge-graph",
            "source": "k8s-live-api",
            "node_count": len(nodes),
            "edge_count": len(links),
        },
        "nodes": list(nodes.values()),
        "links": links,
        "hyperedges": [],
        "diagnostics": diagnostics,
    }


def build_domain_hyperedges(graph: Dict[str, Any], doc_dirs: Optional[List[str]] = None) -> Dict[str, Any]:
    """Build multi-modal Graphify hyperedges linking Markdown ADRs/docs, SQL tables, code symbols, and K8s resources."""
    out = copy.deepcopy(graph)
    nodes_by_id = {n["id"]: n for n in out.get("nodes", [])}
    hyperedges: List[Dict[str, Any]] = list(out.get("hyperedges", []))
    table_re = re.compile(r"(?i)CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_]+)")

    doc_texts: List[Tuple[str, str]] = []
    for d in doc_dirs or []:
        dp = Path(d)
        files = [dp] if dp.is_file() else list(dp.rglob("*"))
        for f in sorted(files):
            if not f.is_file():
                continue
            if f.suffix.lower() == ".sql":
                txt = f.read_text(encoding="utf-8", errors="ignore")
                for m in table_re.finditer(txt):
                    tname = m.group(1)
                    tid = f"sql:table:{tname}"
                    if tid not in nodes_by_id:
                        node = {
                            "id": tid,
                            "label": f"SQL Table: {tname}",
                            "file_type": "sql_table",
                            "source_file": str(f),
                            "community": 30,
                            "_origin": "sql_schema",
                            "properties": {"table": tname},
                        }
                        out["nodes"].append(node)
                        nodes_by_id[tid] = node
            elif f.suffix.lower() in (".md", ".txt"):
                txt = f.read_text(encoding="utf-8", errors="ignore")
                did = f"doc:{f.name}"
                if did not in nodes_by_id:
                    node = {
                        "id": did,
                        "label": f"Doc: {f.name}",
                        "file_type": "markdown_doc",
                        "source_file": str(f),
                        "community": 30,
                        "_origin": "markdown_doc",
                        "properties": {},
                    }
                    out["nodes"].append(node)
                    nodes_by_id[did] = node
                doc_texts.append((did, txt))

    for did, txt in doc_texts:
        lower_txt = txt.lower()
        members = [did]
        for nid, n in nodes_by_id.items():
            if nid == did:
                continue
            short = nid.rsplit("/", 1)[-1].split(":")[-1].split(".")[-1]
            if len(short) >= 3 and (short in txt or short.lower() in lower_txt):
                members.append(nid)
        if len(members) >= 2:
            hyperedges.append(
                {
                    "id": f"hyperedge:{did}",
                    "label": f"Domain Concept ({did})",
                    "nodes": sorted(set(members)),
                    "confidence": "INFERRED",
                    "confidence_score": 0.85,
                }
            )

    out["hyperedges"] = hyperedges
    return out


def _parse_manifest_targets(file_path: Path) -> List[str]:
    """Extracts canonical k8s node IDs defined in a YAML manifest file (skips unrendered Helm templates)."""
    try:
        import yaml

        text = file_path.read_text(encoding="utf-8")
    except Exception:
        return []
    if "{{" in text:
        return []
    targets: List[str] = []
    try:
        for doc in yaml.safe_load_all(text):
            if not isinstance(doc, dict):
                continue
            items = doc.get("items", []) if doc.get("kind", "").endswith("List") else [doc]
            for o in items:
                if (
                    isinstance(o, dict)
                    and o.get("apiVersion")
                    and o.get("kind")
                    and isinstance(o.get("metadata"), dict)
                ):
                    name = o["metadata"].get("name")
                    if name:
                        ns = o["metadata"].get("namespace")
                        if not ns and o["kind"] not in CLUSTER_SCOPED_KINDS:
                            ns = "default"
                        targets.append(canonical_node_id(str(o["apiVersion"]), str(o["kind"]), ns, str(name)))
    except Exception:
        return []
    return targets


# Terraform kubernetes provider resource type -> (api group in canonical ids, Kind)
TF_K8S_KINDS = {
    "kubernetes_namespace": ("core", "Namespace"),
    "kubernetes_namespace_v1": ("core", "Namespace"),
    "kubernetes_deployment": ("apps", "Deployment"),
    "kubernetes_deployment_v1": ("apps", "Deployment"),
    "kubernetes_stateful_set": ("apps", "StatefulSet"),
    "kubernetes_stateful_set_v1": ("apps", "StatefulSet"),
    "kubernetes_daemon_set_v1": ("apps", "DaemonSet"),
    "kubernetes_service": ("core", "Service"),
    "kubernetes_service_v1": ("core", "Service"),
    "kubernetes_service_account": ("core", "ServiceAccount"),
    "kubernetes_service_account_v1": ("core", "ServiceAccount"),
    "kubernetes_config_map": ("core", "ConfigMap"),
    "kubernetes_config_map_v1": ("core", "ConfigMap"),
    "kubernetes_persistent_volume_claim": ("core", "PersistentVolumeClaim"),
    "kubernetes_persistent_volume_claim_v1": ("core", "PersistentVolumeClaim"),
    "kubernetes_ingress_v1": ("networking.k8s.io", "Ingress"),
    "kubernetes_cluster_role": ("rbac.authorization.k8s.io", "ClusterRole"),
    "kubernetes_cluster_role_v1": ("rbac.authorization.k8s.io", "ClusterRole"),
    "kubernetes_role_v1": ("rbac.authorization.k8s.io", "Role"),
}
HELM_OWNED_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "Service"}


def bridge_terraform(nodes: Dict[str, Dict[str, Any]]) -> List[Tuple[str, str]]:
    """Returns (terraform node id, k8s node id) pairs for `provisions-k8s` links.

    helm_release -> its Namespace plus workloads/Services named <release> or <release>-*; kubernetes_* -> the
    exact canonical resource when name (and namespace) are literal in HCL. Unresolved interpolations never link."""
    pairs: List[Tuple[str, str]] = []
    for nid, n in nodes.items():
        p = n.get("properties") or {}
        tf_type = p.get("tf_type", "")
        if not nid.startswith("resource:") or not tf_type:
            continue
        if tf_type == "helm_release":
            rel, ns = p.get("name"), p.get("namespace")
            if not rel or not ns:
                continue
            ns_id = canonical_node_id("v1", "Namespace", None, ns)
            if ns_id in nodes:
                pairs.append((nid, ns_id))
            for kid, kn in nodes.items():
                kp = kn.get("properties") or {}
                if (
                    kid.startswith("k8s:")
                    and kp.get("namespace") == ns
                    and kp.get("kind") in HELM_OWNED_KINDS
                    and (kp.get("name") == rel or str(kp.get("name", "")).startswith(rel + "-"))
                ):
                    pairs.append((nid, kid))
        elif tf_type in TF_K8S_KINDS:
            group, kind = TF_K8S_KINDS[tf_type]
            name = p.get("k8s_name")
            if not name:
                continue
            ns = None if kind in CLUSTER_SCOPED_KINDS else (p.get("k8s_namespace") or "default")
            kid = f"k8s:{group}/{kind}/{ns or '_cluster_'}/{name}"
            if kid in nodes:
                pairs.append((nid, kid))
    return pairs


def _ref_values(val: Any) -> List[Tuple[str, str, str]]:
    """(name, kind, namespace) triples from a reference-shaped value: string, {name,kind,namespace}, or a list."""
    if isinstance(val, str):
        return [(val, "", "")]
    if isinstance(val, dict) and isinstance(val.get("name"), str):
        return [(val["name"], str(val.get("kind", "")), str(val.get("namespace", "")))]
    if isinstance(val, list):
        return [t for v in val for t in _ref_values(v)]
    return []


def _get_path(obj: Any, path: str) -> List[Any]:
    cur = [obj]
    for part in path.split("."):
        nxt: List[Any] = []
        for c in cur:
            if isinstance(c, list):
                c = [x.get(part) for x in c if isinstance(x, dict)]
                nxt.extend(v for v in c if v is not None)
            elif isinstance(c, dict) and part in c:
                nxt.append(c[part])
        cur = nxt
    return cur


def schema_ref_edges(graph: Dict[str, Any], objects: List[Dict[str, Any]], catalog: Dict[str, Any]) -> Dict[str, Any]:
    """Adds `references` links from CRD/OpenAPI-discovered reference fields (k8s_catalog ref_fields) to existing nodes.

    Targets are matched by name (+ kind and namespace when the field carries them) among nodes already in the graph;
    nothing is invented, so an unresolved reference adds no edge."""
    out = copy.deepcopy(graph)
    by_name: Dict[str, List[Dict[str, Any]]] = {}
    for n in out["nodes"]:
        p = n.get("properties") or {}
        if n["id"].startswith("k8s:") and p.get("name"):
            by_name.setdefault(p["name"], []).append(n)
    have = {(lk["source"], lk["relation"], lk["target"]) for lk in out["links"]}
    for o in objects:
        meta = o.get("metadata", {})
        api = o.get("apiVersion", "v1")
        group = api.rsplit("/", 1)[0] if "/" in api else "core"
        fields = (catalog.get(f"{group}/{o.get('kind')}") or {}).get("ref_fields", [])
        src = canonical_node_id(api, o.get("kind", ""), meta.get("namespace"), meta.get("name", ""))
        if src not in {n["id"] for n in out["nodes"]}:
            continue
        for fpath in fields:
            for raw in _get_path(o, fpath):
                for name, kind, ns in _ref_values(raw):
                    for cand in by_name.get(name, []):
                        cp = cand["properties"]
                        if cand["id"] == src or (kind and cp.get("kind") != kind):
                            continue
                        if ns and cp.get("namespace") != ns:
                            continue
                        if not ns and cp.get("namespace") not in (None, meta.get("namespace")):
                            continue
                        key = (src, "references", cand["id"])
                        if key not in have:
                            have.add(key)
                            out["links"].append(
                                {
                                    "source": src,
                                    "target": cand["id"],
                                    "relation": "references",
                                    "_origin": "schema_ref_field",
                                    "confidence": "INFERRED",
                                    "confidence_score": 0.7,
                                    "weight": 1.0,
                                    "field": fpath,
                                }
                            )
    out["graph"]["edge_count"] = len(out["links"])
    return out


def _write_private(path: Path, data: Any) -> None:
    """Cache files hold redacted objects only; still 0600 and secret-scanned like every graph write."""
    write_graph_atomic(path, data)


def merge_graphify_graphs(
    base_graph: Dict[str, Any],
    k8s_graph: Dict[str, Any],
    manifest_dirs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Merges a code Graphify graph with a Kubernetes live cluster graph and bridges YAML manifests."""
    merged_nodes = {n["id"]: copy.deepcopy(n) for n in base_graph.get("nodes", [])}
    for n in k8s_graph.get("nodes", []):
        if n["id"] not in merged_nodes:
            merged_nodes[n["id"]] = copy.deepcopy(n)
        else:
            merged_nodes[n["id"]].setdefault("properties", {}).update(n.get("properties", {}))

    seen_links = set()
    merged_links = []

    def add_merged_link(src: str, rel: str, tgt: str, origin: str = "manifest_bridge"):
        key = (src, rel, tgt)
        if key not in seen_links:
            seen_links.add(key)
            merged_links.append(
                {
                    "source": src,
                    "target": tgt,
                    "relation": rel,
                    "_origin": origin,
                    "confidence": "EXTRACTED",
                    "confidence_score": 1.0,
                    "weight": 1.0,
                }
            )

    for lnk in base_graph.get("links", []) + k8s_graph.get("links", []):
        key = (lnk["source"], lnk.get("relation", "relates"), lnk["target"])
        if key not in seen_links:
            seen_links.add(key)
            merged_links.append(copy.deepcopy(lnk))

    # Index manifest files from manifest_dirs if provided
    manifest_map: Dict[str, List[str]] = {}
    for d in manifest_dirs or []:
        dp = Path(d)
        files = [dp] if dp.is_file() else list(dp.rglob("*.y*ml"))
        for f in files:
            tids = _parse_manifest_targets(f)
            if tids:
                manifest_map[str(f.resolve())] = tids
                manifest_map[str(f)] = tids

    # Connect manifest code nodes to live k8s nodes dynamically, with fallback for synthetic paths
    for nid, node in merged_nodes.items():
        src_file = node.get("source_file", "")
        if not src_file or src_file.startswith("k8s://"):
            continue
        matched_targets: List[str] = []
        if src_file in manifest_map:
            matched_targets.extend(manifest_map[src_file])
        elif Path(src_file).is_file():
            matched_targets.extend(_parse_manifest_targets(Path(src_file)))

        for tid in matched_targets:
            if tid in merged_nodes:
                add_merged_link(nid, "manifest-of", tid)

    for tf_id, k_id in bridge_terraform(merged_nodes):
        add_merged_link(tf_id, "provisions-k8s", k_id, origin="terraform_bridge")

    return {
        "directed": True,
        "multigraph": False,
        "graph": {
            "name": "unified-code-and-cluster-graph",
            "node_count": len(merged_nodes),
            "edge_count": len(merged_links),
        },
        "nodes": list(merged_nodes.values()),
        "links": merged_links,
        "hyperedges": list(base_graph.get("hyperedges", [])) + list(k8s_graph.get("hyperedges", [])),
    }


def _paths_match(sfile: str, rec_path: str) -> bool:
    """Matches paths only on exact equality or full path-component boundary (never partial filename suffix)."""
    if not sfile or not rec_path or sfile.startswith("k8s://"):
        return False
    sp, rp = Path(sfile).parts, Path(rec_path).parts
    if not sp or not rp:
        return False
    if sp == rp:
        return True
    if len(sp) > len(rp):
        return sp[-len(rp) :] == rp
    return rp[-len(sp) :] == sp


def enrich_with_ast_records(graph: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Attaches skill-code-map local_extract.py AST rule records onto matching Graphify nodes."""
    out = copy.deepcopy(graph)
    nodes = out.get("nodes", [])
    for rec in records:
        rec_path = rec.get("path", "")
        rec_name = rec.get("source_name", "")
        scope = rec.get("source_scope", "")
        payload = {
            "record_type": rec.get("record_type"),
            "record_id": rec.get("record_id"),
            "source_scope": scope,
            "line": rec.get("line"),
            "extracted_data": rec.get("extracted_data", {}),
        }
        symbol_hits = [
            node
            for node in nodes
            if rec_name
            and scope != "file"
            and (
                node.get("id", "") == rec_name
                or node.get("id", "").endswith(f":{rec_name}")
                or node.get("id", "").endswith(f".{rec_name}")
                or node.get("label", "") == rec_name
            )
            and (not rec_path or not node.get("source_file") or _paths_match(node.get("source_file", ""), rec_path))
        ]
        targets = (
            symbol_hits
            if symbol_hits
            else [node for node in nodes if _paths_match(node.get("source_file", ""), rec_path)]
        )
        for node in targets:
            node.setdefault("properties", {}).setdefault("ast_records", []).append(dict(payload))
    return out


def main():
    parser = argparse.ArgumentParser(description="Extract Kubernetes live state into Graphify knowledge graph format.")
    parser.add_argument(
        "--namespace", "-n", default="cloud-boot-app", help="Target namespace (default: cloud-boot-app)"
    )
    parser.add_argument("--all-namespaces", "-A", action="store_true", help="Extract across all Kubernetes namespaces")
    parser.add_argument("--kubeconfig", default=None, help="Path to kubeconfig")
    parser.add_argument("--context", default=None, help="kubectl context")
    parser.add_argument("--allow-prod-read", action="store_true", help="Permit read-only access to a *prod* context")
    parser.add_argument("--live-k8s", default=None, help="Offline JSON list of Kubernetes objects instead of kubectl")
    parser.add_argument(
        "--manifests", nargs="*", default=None, help="Repo manifest directories to bridge with live cluster"
    )
    parser.add_argument(
        "--docs", nargs="*", default=None, help="Doc/ADR/SQL directories to link via multi-modal hyperedges"
    )
    parser.add_argument(
        "--extract-rules", nargs="*", default=None, help="Run skill-code-map local_extract.py on dirs and enrich graph"
    )
    parser.add_argument(
        "--out", default="projects/cloud-boot-app/graphify-out/k8s-graph.json", help="Output path for graph JSON"
    )
    parser.add_argument("--merge-with", default=None, help="Path to base Graphify graph.json to merge with")
    parser.add_argument(
        "--export-html", action="store_true", help="Automatically generate Graphify interactive HTML visualization"
    )

    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Directory for redacted objects.json and schema catalog.json; reused by --no-live",
    )
    parser.add_argument(
        "--no-live", action="store_true", help="Never call the cluster: build from --cache-dir (objects + catalog)"
    )
    parser.add_argument("--catalog", default=None, help="k8s_catalog catalog JSON for schema-driven reference edges")
    parser.add_argument(
        "--discover-schema", action="store_true", help="Read OpenAPI v3 + CRDs (no instances) for reference fields"
    )

    args = parser.parse_args()
    cache = Path(args.cache_dir) if args.cache_dir else None
    if args.no_live and not (cache and (cache / "objects.json").is_file()):
        sys.exit("--no-live needs --cache-dir containing objects.json from a previous live run")
    if args.no_live:
        args.live_k8s = str(cache / "objects.json")

    if not args.live_k8s:
        ctx = args.context
        if not ctx:
            raw_ctx = run_kubectl(["config", "current-context"], kubeconfig=args.kubeconfig)
            ctx = raw_ctx.strip() if isinstance(raw_ctx, str) else ""
        check_prod_context(ctx, allow_prod_read=args.allow_prod_read)

    if args.live_k8s:
        raw = json.loads(Path(args.live_k8s).read_text(encoding="utf-8"))
        items = raw.get("items", []) if isinstance(raw, dict) else raw
        objects = [redact(o) for o in items if not scan_for_secrets(redact(o))]
    else:
        target_desc = "all namespaces" if args.all_namespaces else f"namespace '{args.namespace}'"
        print(f"[*] Querying Kubernetes API for {target_desc}...")
        objects = fetch_cluster_resources(
            namespace=args.namespace if not args.all_namespaces else None,
            all_namespaces=args.all_namespaces,
            kubeconfig=args.kubeconfig,
            context=args.context,
        )
    print(f"[*] Fetched and redacted {len(objects)} live Kubernetes objects.")
    if cache and not args.no_live:
        _write_private(cache / "objects.json", objects)

    catalog: Dict[str, Any] = {}
    if args.catalog and os.path.exists(args.catalog):
        raw_cat = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
        catalog = raw_cat.get("catalog", raw_cat)
    elif cache and (cache / "catalog.json").is_file() and not args.discover_schema:
        catalog = json.loads((cache / "catalog.json").read_text(encoding="utf-8"))
    elif args.discover_schema and not args.no_live:
        from k8s_catalog import _ctx_args

        catalog = discover_catalog(_ctx_args(args.context, args.kubeconfig))
        if cache:
            _write_private(cache / "catalog.json", catalog)

    k8s_graph = build_graphify_k8s_graph(objects)
    if catalog:
        k8s_graph = schema_ref_edges(k8s_graph, objects, catalog)
    print(
        f"[*] Generated Kubernetes knowledge graph: {len(k8s_graph['nodes'])} nodes, {len(k8s_graph['links'])} links."
    )

    output_path = Path(args.out)
    final_graph = k8s_graph
    if args.merge_with and os.path.exists(args.merge_with):
        print(f"[*] Merging with existing Graphify graph from {args.merge_with}...")
        with open(args.merge_with, "r", encoding="utf-8") as f:
            base_graph = json.load(f)
        final_graph = merge_graphify_graphs(base_graph, k8s_graph, manifest_dirs=args.manifests)
        print(f"[*] Unified graph: {len(final_graph['nodes'])} nodes, {len(final_graph['links'])} links.")

    if args.docs:
        final_graph = build_domain_hyperedges(final_graph, doc_dirs=args.docs)

    if args.extract_rules:
        le_script = Path(__file__).resolve().parents[2] / "skill-code-map" / "scripts" / "local_extract.py"
        if le_script.is_file():
            proc = subprocess.run([sys.executable, str(le_script), *args.extract_rules], capture_output=True, text=True)
            if proc.returncode == 0 and proc.stdout.strip():
                recs = json.loads(proc.stdout).get("records", [])
                final_graph = enrich_with_ast_records(final_graph, recs)

    write_graph_atomic(output_path, final_graph)
    print(f"[+] Output written atomically (0600) to: {output_path}")

    if args.export_html:
        print("[*] Generating interactive Graphify HTML visualization...")
        subprocess.run(["graphify", "export", "html", "--graph", str(output_path)])


if __name__ == "__main__":
    main()
