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


class SecretLeakError(RuntimeError):
    """Raised when a secret-shaped value survives redaction before disk write."""


NEVER_LIST = {"secrets", "configmaps", "tokenreviews", "tokenrequests", "serviceaccounts/token"}
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


def check_prod_context(context: Optional[str], allow_prod_read: bool = False) -> None:
    """Refuses read access to a kubectl context containing 'prod' unless explicitly permitted."""
    if context and "prod" in context.lower() and not allow_prod_read:
        sys.exit(
            f"refusing: kubectl context '{context}' looks like production; pass --allow-prod-read for read-only access"
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

    discovered_resources: List[str] = []
    if dynamic_discovery:
        api_out = run_kubectl(["api-resources", "--verbs=list", "-o", "name"], kubeconfig, context=context)
        if isinstance(api_out, str) and api_out.strip():
            discovered_resources = [
                r.strip() for r in api_out.splitlines() if r.strip() and r.strip().split(".")[0] not in NEVER_LIST
            ]

    if discovered_resources:
        # Query core + discovered CRD groups safely without ever listing secrets/configmaps
        queries = [["get", r, "-A", "-o", "json", "--ignore-not-found"] for r in discovered_resources]
    else:
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
        data = run_kubectl(q, kubeconfig, context=context)
        if isinstance(data, dict):
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

    def ensure_phantom_node(nid: str, kind: str, ns: Optional[str], name: str, community: int = 10) -> None:
        if nid not in nodes:
            nodes[nid] = {
                "id": nid,
                "label": f"{kind}: {name}",
                "file_type": "k8s_resource",
                "source_file": f"k8s://{ns or 'cluster'}/{kind.lower()}/{name}",
                "source_location": "k8s-api",
                "community": community,
                "_origin": "k8s_api",
                "properties": {"kind": kind, "namespace": ns, "name": name, "status": "Referenced"},
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
                ensure_phantom_node(comp_id, "Composition", None, comp_name, community=11)
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
                ensure_phantom_node(sec_id, "Secret", sec_ns, v["name"], community=10)
                add_link(src_id, "references-secret", sec_id)
            elif k in ("secretName", "tlsSecretName") and isinstance(v, str) and v != REDACTED:
                sec_ns = ns or "default"
                sec_id = canonical_node_id("v1", "Secret", sec_ns, v)
                ensure_phantom_node(sec_id, "Secret", sec_ns, v, community=10)
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
            ensure_phantom_node(sa_id, "ServiceAccount", wl_ns or "default", sa_name, community=10)
            add_link(wl_id, "uses-serviceaccount", sa_id)

    for dep in deployments:
        dep_id = canonical_node_id(
            dep["apiVersion"], dep["kind"], dep["metadata"].get("namespace"), dep["metadata"]["name"]
        )
        db_svc_id = canonical_node_id("v1", "Service", dep["metadata"].get("namespace"), "cloud-boot-db")
        if db_svc_id in nodes:
            add_link(dep_id, "connects-db", db_svc_id)

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
            ensure_phantom_node(r_id, r_kind, r_ns, role_ref["name"], community=10)
            add_link(rb_id, "grants-role", r_id)
        for subj in obj.get("subjects") or []:
            if isinstance(subj, dict) and subj.get("kind") == "ServiceAccount" and subj.get("name"):
                s_ns = subj.get("namespace") or ns or "default"
                sa_id = canonical_node_id("v1", "ServiceAccount", s_ns, subj["name"])
                ensure_phantom_node(sa_id, "ServiceAccount", s_ns, subj["name"], community=10)
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

    args = parser.parse_args()

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

    k8s_graph = build_graphify_k8s_graph(objects)
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
