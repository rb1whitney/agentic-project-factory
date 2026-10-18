#!/usr/bin/env python3
"""IaC-vs-live state graph for Kubernetes and Vault (skill-code-map). Read-only.

Desired state: Kubernetes manifests and vault_controller YAML payloads (`api_paths:`).
Live state: `kubectl get` and `vault read|list` only. Secret payloads are stripped at the fetch
boundary and never reach a report; values under sensitive keys are redacted in every diff.
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from k8s_catalog import REDACTED, SENSITIVE_KEY  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("state_graph")

ABSENT = "<absent>"
SKIP_DIRS = {".git", "vendor", "node_modules", ".ast_cache", "__pycache__", ".venv", "venv"}
CLUSTER_SCOPED = {
    "Namespace",
    "Node",
    "PersistentVolume",
    "StorageClass",
    "ClusterRole",
    "ClusterRoleBinding",
    "CustomResourceDefinition",
    "PriorityClass",
    "IngressClass",
    "ValidatingWebhookConfiguration",
    "MutatingWebhookConfiguration",
    "APIService",
    "CSIDriver",
    "RuntimeClass",
}
SECRET_PAYLOAD_KEYS = ("data", "stringData", "binaryData")
VAULT_ANNOTATION = "vault.hashicorp.com/role"
# Objects the cluster or a controller creates on its own; reporting them as "unmanaged" is noise.
GENERATED_NAMES = {("ConfigMap", "kube-root-ca.crt"), ("ServiceAccount", "default"), ("Service", "kubernetes")}
GENERATED_SECRET_TYPES = ("helm.sh/release.v1", "kubernetes.io/service-account-token")
VAULT_BUILTIN = {
    "policy": {"root", "default"},
    "mount": {"sys", "cubbyhole", "identity"},
    "auth": {"token"},
    "audit": set(),
}


# ------------------------------------------------------------------ diff core


def _scrub(val: Any, key: str = "") -> Any:
    if SENSITIVE_KEY.search(key) and not isinstance(val, (dict, list)):
        return REDACTED
    if isinstance(val, dict):
        return {k: _scrub(v, k) for k, v in val.items()}
    if isinstance(val, list):
        return [_scrub(v, key) for v in val]
    return val


def _norm(v: Any) -> str:
    return str(v).lower() if isinstance(v, bool) else str(v)


def subset_diff(desired: Any, live: Any, path: str = "") -> List[Dict[str, Any]]:
    """Fields set in `desired` that differ in `live`. Extra live fields (defaults, status) are ignored."""
    out: List[Dict[str, Any]] = []

    def change(p: str, d: Any, lv: Any) -> None:
        key = p.rsplit(".", 1)[-1].split("[")[0]
        out.append({"path": p, "desired": _scrub(d, key), "live": _scrub(lv, key)})

    if isinstance(desired, dict):
        if not isinstance(live, dict):
            change(path, desired, live)
            return out
        for k, dv in desired.items():
            p = f"{path}.{k}" if path else str(k)
            if k not in live:
                change(p, dv, ABSENT)
            else:
                out.extend(subset_diff(dv, live[k], p))
    elif isinstance(desired, list):
        if not isinstance(live, list):
            change(path, desired, live)
        elif (
            desired
            and all(isinstance(x, dict) and "name" in x for x in desired)
            and all(isinstance(x, dict) and "name" in x for x in live)
        ):
            by_name = {x["name"]: x for x in live}
            for dx in desired:
                p = f"{path}[{dx['name']}]"
                if dx["name"] not in by_name:
                    change(p, dx, ABSENT)
                else:
                    out.extend(subset_diff(dx, by_name[dx["name"]], p))
        elif len(desired) != len(live):
            change(path, desired, live)
        else:
            for i, (dx, lx) in enumerate(zip(desired, live)):
                out.extend(subset_diff(dx, lx, f"{path}[{i}]"))
    elif _norm(desired) != _norm(live):
        change(path, desired, live)
    return out


# ------------------------------------------------------------------ Kubernetes


def _k8s_id(obj: Dict[str, Any]) -> str:
    md = obj.get("metadata", {})
    ns = md.get("namespace") or ("" if obj["kind"] in CLUSTER_SCOPED else "default")
    return f"{obj['apiVersion']}/{obj['kind']}/{ns}/{md['name']}"


def _split_id(obj_id: str) -> Tuple[str, str, str, str]:
    parts = obj_id.split("/")
    # Version is dropped so a v1beta1 manifest matches the v1 object the server returns.
    # core: v1/Kind/ns/name ; grouped: group/version/Kind/ns/name
    if len(parts) == 4:
        return "", parts[1], parts[2], parts[3]
    return parts[0], parts[2], parts[3], "/".join(parts[4:])


def _walk_files(paths: Iterable[str], suffixes: Tuple[str, ...]) -> Iterable[Path]:
    for p in paths:
        pp = Path(p)
        if pp.is_file():
            yield pp
            continue
        for dirpath, dirs, names in os.walk(pp):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for n in sorted(names):
                if n.endswith(suffixes):
                    yield Path(dirpath) / n


def load_k8s_desired(paths: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for f in _walk_files(paths, (".yaml", ".yml", ".json")):
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "{{" in text:  # unrendered helm/go template
            continue
        try:
            docs = list(yaml.safe_load_all(text))
        except yaml.YAMLError:
            continue
        for doc in docs:
            items = doc.get("items", []) if isinstance(doc, dict) and doc.get("kind", "").endswith("List") else [doc]
            for o in items:
                if not (
                    isinstance(o, dict)
                    and isinstance(o.get("apiVersion"), str)
                    and isinstance(o.get("kind"), str)
                    and isinstance(o.get("metadata"), dict)
                    and o["metadata"].get("name")
                ):
                    continue
                o = dict(o)
                if o["kind"] == "Secret":
                    for k in SECRET_PAYLOAD_KEYS:
                        o.pop(k, None)
                    if isinstance(o.get("metadata"), dict):
                        o["metadata"] = dict(o["metadata"])
                        o["metadata"].pop("annotations", None)
                o["_source"] = str(f)
                out[_k8s_id(o)] = o
    return out


def desired_scope(desired: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    scope: Dict[str, set] = {}
    for o in desired.values():
        ns = o["metadata"].get("namespace") or ("" if o["kind"] in CLUSTER_SCOPED else "default")
        scope.setdefault(f"{o['apiVersion']}/{o['kind']}", set()).add(ns)
    return {k: sorted(v) for k, v in scope.items()}


def _kubectl_runner(context: Optional[str] = None) -> Callable[[List[str]], Optional[str]]:
    def run(args: List[str]) -> Optional[str]:
        cmd = ["kubectl"] + (["--context", context] if context else []) + args
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.warning("kubectl %s failed: %s", " ".join(args[:3]), res.stderr.strip()[:200])
            return None
        return res.stdout

    return run


def _strip_secret(item: Dict[str, Any]) -> Dict[str, Any]:
    if item.get("kind") == "Secret":
        for k in SECRET_PAYLOAD_KEYS:
            item.pop(k, None)
        item.get("metadata", {}).pop("annotations", None)  # last-applied copies carry the payload
    return item


def fetch_k8s_live(
    scope: Dict[str, List[str]], runner: Optional[Callable[[List[str]], Optional[str]]] = None
) -> List[Dict[str, Any]]:
    runner = runner or _kubectl_runner()
    live: List[Dict[str, Any]] = []
    for api_kind, namespaces in sorted(scope.items()):
        api, kind = api_kind.rsplit("/", 1)
        group = api.split("/")[0] if "/" in api else ""
        res = f"{kind}.{group}" if group else kind
        targets = [[]] if kind in CLUSTER_SCOPED else [["-n", ns] for ns in (namespaces or [])] or [["-A"]]
        for t in targets:
            out = runner(["get", res, *t, "-o", "json", "--ignore-not-found"])
            if not out:
                continue
            try:
                items = json.loads(out).get("items", [])
            except json.JSONDecodeError:
                continue
            for it in items:
                it.setdefault("apiVersion", api)
                it.setdefault("kind", kind)
                live.append(_strip_secret(it))
    return live


def _is_generated(o: Dict[str, Any]) -> bool:
    md = o.get("metadata", {})
    if md.get("ownerReferences"):
        return True
    if (o["kind"], md.get("name")) in GENERATED_NAMES:
        return True
    return o["kind"] == "Secret" and o.get("type") in GENERATED_SECRET_TYPES


def diff_k8s(desired: Dict[str, Dict[str, Any]], live: List[Dict[str, Any]]) -> Dict[str, Any]:
    live_by_key = {_split_id(_k8s_id(o)): o for o in live}
    desired_keys = {_split_id(i): i for i in desired}
    missing, drifted = [], []
    for did, dobj in sorted(desired.items()):
        lobj = live_by_key.get(_split_id(did))
        if lobj is None:
            missing.append(did)
            continue
        if dobj["kind"] == "Secret":
            continue  # identity only; payloads are never compared
        changes: List[Dict[str, Any]] = []
        for k, v in dobj.items():
            if k in ("apiVersion", "kind", "metadata", "status", "_source"):
                continue
            changes.extend(subset_diff(v, lobj.get(k, ABSENT), k))
        labels = dobj["metadata"].get("labels")
        if labels:
            changes.extend(subset_diff(labels, lobj.get("metadata", {}).get("labels", {}), "metadata.labels"))
        if changes:
            drifted.append({"id": did, "changes": changes})
    unmanaged = sorted(_k8s_id(o) for o in live if _split_id(_k8s_id(o)) not in desired_keys and not _is_generated(o))
    return {"missing": missing, "drifted": drifted, "unmanaged": unmanaged}


# ------------------------------------------------------------------ cluster health

_BAD_WAIT = {
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "CreateContainerConfigError",
    "CreateContainerError",
}


def cluster_health(objs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []

    def add(kind: str, o: Dict[str, Any], detail: str) -> None:
        md = o["metadata"]
        out.append(
            {
                "kind": kind,
                "id": f"{md['namespace']}/{md['name']}" if md.get("namespace") else md["name"],
                "detail": detail,
            }
        )

    pods = [o for o in objs if o.get("kind") == "Pod"]
    for o in objs:
        kind, st, spec = o.get("kind"), o.get("status", {}), o.get("spec", {})
        if kind == "Pod":
            phase = st.get("phase", "")
            if phase == "Succeeded":
                continue
            reasons = [c.get("state", {}).get("waiting", {}).get("reason", "") for c in st.get("containerStatuses", [])]
            bad = [r for r in reasons if r in _BAD_WAIT]
            notready = [c["name"] for c in st.get("containerStatuses", []) if not c.get("ready")]
            if phase in ("Pending", "Failed", "Unknown") or bad or notready:
                add("pod-unready", o, ", ".join(bad) or f"phase={phase} notReady={notready}")
        elif kind in ("Deployment", "StatefulSet"):
            want, have = spec.get("replicas", 1), st.get("readyReplicas", 0)
            if want > have:
                add("workload-underreplicated", o, f"{have}/{want} ready")
        elif kind == "DaemonSet":
            want, have = st.get("desiredNumberScheduled", 0), st.get("numberReady", 0)
            if want > have:
                add("workload-underreplicated", o, f"{have}/{want} ready")
        elif kind == "Node":
            ready = [c for c in st.get("conditions", []) if c.get("type") == "Ready"]
            if not ready or ready[0].get("status") != "True":
                add("node-not-ready", o, "Ready!=True")
        elif kind == "PersistentVolumeClaim" and st.get("phase") == "Pending":
            add("pvc-pending", o, "Pending")
        elif kind == "Service" and spec.get("selector"):
            ns = o["metadata"].get("namespace")
            hit = any(
                p["metadata"].get("namespace") == ns
                and all(p["metadata"].get("labels", {}).get(k) == v for k, v in spec["selector"].items())
                for p in pods
            )
            if not hit:
                add("service-no-endpoints-selector", o, f"selector {spec['selector']} matches no pod")
    return out


def fetch_health_objs(runner: Optional[Callable[[List[str]], Optional[str]]] = None) -> List[Dict[str, Any]]:
    runner = runner or _kubectl_runner()
    out = runner(
        ["get", "pods,deployments,statefulsets,daemonsets,nodes,pvc,services", "-A", "-o", "json", "--ignore-not-found"]
    )
    try:
        return json.loads(out).get("items", []) if out else []
    except json.JSONDecodeError:
        return []


# ------------------------------------------------------------------ Vault: desired


def _ttl(v: Any) -> Any:
    if isinstance(v, str):
        m = re.match(r"^(\d+)([smhd]?)$", v.strip().lower())
        if m:
            return int(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]
    return v


def _norm_vault(v: Any, key: str = "") -> Any:
    if isinstance(v, dict):
        return {k: _norm_vault(x, k) for k, x in v.items()}
    if isinstance(v, list):
        items = [_norm_vault(x, key) for x in v]
        return sorted(items, key=str) if all(not isinstance(x, (dict, list)) for x in items) else items
    return _ttl(v) if key.endswith("_ttl") or key.endswith("ttl") else v


def classify_vault_path(api_path: str) -> Tuple[str, str]:
    p = api_path.strip("/")
    p = p[3:] if p.startswith("v1/") else p
    for pat, kind in (
        (r"^sys/policies/acl/(.+)$", "policy"),
        (r"^sys/policy/(.+)$", "policy"),
        (r"^sys/mounts/(.+)$", "mount"),
        (r"^sys/auth/(.+)$", "auth"),
        (r"^sys/audit/(.+)$", "audit"),
    ):
        m = re.match(pat, p)
        if m:
            return kind, m.group(1).strip("/")
    m = re.match(r"^auth/([^/]+)/role/(.+)$", p)
    if m:
        return "auth_role", f"{m.group(1)}/{m.group(2)}"
    m = re.match(r"^auth/([^/]+)/config$", p)
    if m:
        return "auth_config", m.group(1)
    if re.match(r"^[^/]+/data/.+", p):
        return "secret", p
    return "other", p


def _vault_files(root: Path) -> Iterable[Tuple[Path, Dict[str, Any]]]:
    for f in _walk_files([str(root)], (".yaml", ".yml")):
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        if isinstance(doc, dict) and isinstance(doc.get("api_paths"), list):
            yield f, doc


def load_vault_desired(root: Path) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for f, doc in _vault_files(Path(root)):
        ns = str(doc.get("_namespace") or "")
        for obj in doc["api_paths"]:
            if not isinstance(obj, dict) or obj.get("api_action") not in ("post", "put", "create", "update", None):
                continue
            kind, name = classify_vault_path(str(obj.get("api_path", "")))
            if kind in ("secret", "other"):
                continue
            out[f"vault:{ns}:{kind}:{name}"] = {
                "kind": kind,
                "name": name,
                "namespace": ns,
                "payload": obj.get("api_payload") or {},
                "file": str(f),
            }
    return out


def parse_policy(text: Any) -> Dict[str, List[str]]:
    if isinstance(text, dict):
        text = json.dumps(text)
    text = text or ""
    try:
        doc = json.loads(text)
        return {p: sorted(v.get("capabilities", [])) for p, v in doc.get("path", {}).items()}
    except (json.JSONDecodeError, AttributeError):
        pass
    out: Dict[str, List[str]] = {}
    starts = list(re.finditer(r'path\s+"([^"]+)"\s*\{', text))
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        cap = re.search(r"capabilities\s*=\s*\[(.*?)\]", text[m.end() : end], re.DOTALL)
        out[m.group(1)] = sorted(re.findall(r'"([^"]+)"', cap.group(1))) if cap else []
    return out


def _walk_payload(obj: Any, key: str = "") -> Iterable[Tuple[str, Any]]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from _walk_payload(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_payload(v, key)


def lint_vault(root: Path) -> List[Dict[str, str]]:
    """Static checks. `repo-rule` mirrors vault_controller's ValidationManager; `advisory` is added hardening."""
    root = Path(root)
    out: List[Dict[str, str]] = []

    def add(rule: str, sev: str, f: Any, msg: str) -> None:
        out.append({"rule": rule, "severity": sev, "file": str(f), "message": msg})

    for f, doc in _vault_files(root):
        ns = doc.get("_namespace")
        parts = f.resolve().parts
        if ns == "root":
            add("root-namespace", "repo-rule", f, "root namespace is prohibited in payloads")
        if "namespaces" in parts and ns and ns != parts[parts.index("namespaces") + 1]:
            add("namespace-dir-mismatch", "repo-rule", f, f"_namespace {ns} != parent directory")
        in_kv = "kv" in parts
        for obj in doc["api_paths"]:
            if not isinstance(obj, dict):
                continue
            path, action, payload = str(obj.get("api_path", "")), obj.get("api_action"), obj.get("api_payload") or {}
            kind, name = classify_vault_path(path)
            if ".." in path:
                add("path-traversal", "repo-rule", f, f"{path}")
            if in_kv and (kind == "policy" or action in ("delete", "list")):
                add("secret-scheme-forbidden", "repo-rule", f, f"{action} {path} not allowed in secrets deployment")
            if kind == "policy" and isinstance(payload.get("path"), dict):
                for p, caps in payload["path"].items():
                    c = caps.get("capabilities", []) if isinstance(caps, dict) else []
                    if ("read" in c or "list" in c) and any(x in c for x in ("create", "update", "delete")):
                        add("policy-read-write-mix", "repo-rule", f, f"{name}: {p} mixes read and write")
            if kind == "mount":
                ttl = _ttl((payload.get("config") or {}).get("default_lease_ttl", 0))
                if isinstance(ttl, int) and ttl > 3600:
                    add("mount-ttl-over-1h", "repo-rule", f, f"{name}: default_lease_ttl {ttl}s exceeds 1h")
            if kind == "secret" and isinstance(payload.get("data"), dict):
                for k, v in payload["data"].items():
                    if isinstance(v, str) and not v.startswith("vault:v1:"):
                        add("plaintext-secret", "repo-rule", f, f"{path}: key '{k}' is not transit-encrypted")
            if any(k == "insecure_tls" and v is True for k, v in _walk_payload(payload)):
                add("insecure-tls", "advisory", f, f"{path}: insecure_tls true")
            if "/keys/" in path and (
                payload.get("exportable") is True or payload.get("allow_plaintext_backup") is True
            ):
                add("transit-key-exportable", "advisory", f, f"{path}: key is exportable or allows plaintext backup")
            if kind == "audit" and str((payload.get("options") or {}).get("file_path", "")).startswith("/tmp"):
                add("audit-log-in-tmp", "advisory", f, f"{name}: audit log under /tmp")
            if kind == "auth_role":
                names, nss = (
                    payload.get("bound_service_account_names", []),
                    payload.get("bound_service_account_namespaces", []),
                )
                if "*" in (names if isinstance(names, list) else [names]) or "*" in (
                    nss if isinstance(nss, list) else [nss]
                ):
                    add(
                        "wildcard-k8s-role-binding",
                        "advisory",
                        f,
                        f"{name}: binds wildcard service account or namespace",
                    )

    for base in (root, root.parent):
        ctx = base / "contexts.yaml"
        if not ctx.is_file() and (base / "config" / "contexts.yaml").is_file():
            ctx = base / "config" / "contexts.yaml"
        if ctx.is_file():
            try:
                clusters = (yaml.safe_load(ctx.read_text(encoding="utf-8")) or {}).get("clusters", {})
            except (OSError, yaml.YAMLError):
                clusters = {}
            for cname, c in clusters.items():
                if str(c.get("api_url", "localhost")) in ("localhost", "127.0.0.1", "::1"):
                    continue
                if c.get("api_protocol") == "http":
                    add("cleartext-transport", "advisory", ctx, f"cluster {cname}: remote Vault over http")
                if c.get("key_encrypt") is False:
                    add("key-material-unencrypted", "advisory", ctx, f"cluster {cname}: key_encrypt false")
            break
    return out


# ------------------------------------------------------------------ Vault: live


def _vault_cli(args: List[str], ns: str) -> Any:
    cmd = ["vault", args[0], "-format=json"] + ([f"-namespace={ns}"] if ns else []) + args[1:]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        logger.warning("vault %s %s failed: %s", args[0], args[1] if len(args) > 1 else "", res.stderr.strip()[:200])
        return None
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return None


def _vdata(doc: Any) -> Dict[str, Any]:
    if not isinstance(doc, dict):
        return {}
    d = doc.get("data")
    if isinstance(d, dict):
        return d
    return {k: v for k, v in doc.items() if isinstance(v, dict) and k.endswith("/")}


def fetch_vault_live(ns: str = "", runner: Optional[Callable[[List[str], str], Any]] = None) -> Dict[str, Any]:
    runner = runner or _vault_cli
    live: Dict[str, Any] = {"policy": {}, "mount": {}, "auth": {}, "audit": {}, "auth_role": {}}
    for name in runner(["list", "sys/policies/acl"], ns) or []:
        doc = runner(["read", f"sys/policies/acl/{name}"], ns)
        live["policy"][name] = (doc or {}).get("data", {}).get("policy", "")
    live["mount"] = _vdata(runner(["read", "sys/mounts"], ns))
    live["auth"] = _vdata(runner(["read", "sys/auth"], ns))
    live["audit"] = _vdata(runner(["read", "sys/audit"], ns))
    for path, info in live["auth"].items():
        if info.get("type") == "kubernetes":
            mount = path.strip("/")
            for role in runner(["list", f"auth/{mount}/role"], ns) or []:
                live["auth_role"][f"{mount}/{role}"] = (runner(["read", f"auth/{mount}/role/{role}"], ns) or {}).get(
                    "data", {}
                )
    return live


def diff_vault(desired: Dict[str, Dict[str, Any]], live: Dict[str, Any], namespace: str = "") -> Dict[str, Any]:
    missing, drifted = [], []
    seen: Dict[str, set] = {k: set() for k in ("policy", "mount", "auth", "audit", "auth_role")}
    for did, d in sorted(desired.items()):
        if d["namespace"] != namespace:
            continue
        kind, name = d["kind"], d["name"]
        if kind not in seen:
            continue
        seen[kind].add(name)
        bucket = live.get(kind, {})
        entry = bucket.get(name, bucket.get(name + "/"))
        if entry is None:
            missing.append(did)
            continue
        if kind == "policy":
            want = d["payload"].get("path")
            want = (
                {p: sorted(c.get("capabilities", [])) for p, c in want.items()}
                if isinstance(want, dict)
                else parse_policy(d["payload"].get("policy"))
            )
            have = parse_policy(entry)
            changes = [
                {"path": p, "desired": want.get(p, ABSENT), "live": have.get(p, ABSENT)}
                for p in sorted(set(want) | set(have))
                if want.get(p) != have.get(p)
            ]
        else:
            changes = subset_diff(_norm_vault(d["payload"]), _norm_vault(entry))
        if changes:
            drifted.append({"id": did, "changes": changes})
    unmanaged = []
    for kind, bucket in (
        ("policy", live.get("policy", {})),
        ("mount", live.get("mount", {})),
        ("auth", live.get("auth", {})),
        ("audit", live.get("audit", {})),
        ("auth_role", live.get("auth_role", {})),
    ):
        for name in sorted(bucket):
            n = name.strip("/")
            if n not in seen[kind] and n not in VAULT_BUILTIN.get(kind, set()):
                unmanaged.append(f"vault:{namespace}:{kind}:{n}")
    return {"missing": missing, "drifted": drifted, "unmanaged": unmanaged}


# ------------------------------------------------------------------ cross-system


def _annotation_roles(o: Dict[str, Any]) -> List[str]:
    anns = [
        o.get("metadata", {}).get("annotations") or {},
        (o.get("spec", {}).get("template", {}).get("metadata", {}) or {}).get("annotations") or {},
    ]
    return [a[VAULT_ANNOTATION] for a in anns if VAULT_ANNOTATION in a]


def cross_check(
    vault_desired: Dict[str, Dict[str, Any]],
    k8s_desired: Dict[str, Dict[str, Any]],
    k8s_live: List[Dict[str, Any]],
    vault_live: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    sas = {
        (o["metadata"].get("namespace") or "default", o["metadata"]["name"])
        for o in list(k8s_desired.values()) + k8s_live
        if o["kind"] == "ServiceAccount"
    }
    roles = {d["name"].split("/", 1)[1] for d in vault_desired.values() if d["kind"] == "auth_role"}
    roles |= {n.split("/", 1)[1] for n in (vault_live or {}).get("auth_role", {})}
    for d in vault_desired.values():
        if d["kind"] != "auth_role":
            continue
        names, nss = (
            d["payload"].get("bound_service_account_names", []),
            d["payload"].get("bound_service_account_namespaces", []),
        )
        for n in names if isinstance(names, list) else [names]:
            for ns in nss if isinstance(nss, list) else [nss]:
                if "*" in (n, ns):
                    continue
                if (ns, n) not in sas:
                    out.append(
                        {
                            "rule": "role-binds-missing-serviceaccount",
                            "severity": "error",
                            "message": (
                                f"vault role {d['name']} binds ServiceAccount {ns}/{n} "
                                "which is missing from the cluster and manifests"
                            ),
                        }
                    )
    for o in list(k8s_desired.values()) + k8s_live:
        for r in _annotation_roles(o):
            if r not in roles:
                md = o["metadata"]
                out.append(
                    {
                        "rule": "workload-references-unknown-vault-role",
                        "severity": "error",
                        "message": (
                            f"{o['kind']} {md.get('namespace', '')}/{md['name']} "
                            f"annotates vault role {r} that is not defined in Vault config"
                        ),
                    }
                )
    seen = set()
    return [f for f in out if not (f["message"] in seen or seen.add(f["message"]))]


def _canonical_graphify_k8s_id(raw_id: str) -> str:
    """Convert state_graph _k8s_id into canonical k8s:<group>/<Kind>/<ns_or__cluster_>/<name>."""
    if raw_id.startswith("k8s:"):
        return raw_id
    group, kind, ns, name = _split_id(raw_id)
    return f"k8s:{group or 'core'}/{kind}/{ns or '_cluster_'}/{name}"


def report_to_graphify(
    report: Dict[str, Any],
    k8s_desired: Dict[str, Dict[str, Any]],
    vault_desired: Dict[str, Dict[str, Any]],
    k8s_live: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Export IaC-vs-live drift, Vault posture lint, and cross-system bindings as a Graphify graph."""
    nodes: Dict[str, Dict[str, Any]] = {}
    links: List[Dict[str, Any]] = []
    seen_links = set()

    def add_link(src: str, rel: str, tgt: str, weight: float = 1.0) -> None:
        key = (src, rel, tgt)
        if key not in seen_links:
            seen_links.add(key)
            links.append(
                {
                    "source": src,
                    "target": tgt,
                    "relation": rel,
                    "_origin": "state_graph",
                    "confidence": "EXTRACTED",
                    "confidence_score": 1.0,
                    "weight": weight,
                }
            )

    kdrift = report.get("k8s_drift") or {}
    drifted_map = {d["id"]: d["changes"] for d in kdrift.get("drifted", [])}
    missing_set = set(kdrift.get("missing", []))
    unmanaged_set = set(kdrift.get("unmanaged", []))

    for did, obj in k8s_desired.items():
        cid = _canonical_graphify_k8s_id(did)
        status = "drifted" if did in drifted_map else ("missing" if did in missing_set else "in-sync")
        comm = 21 if status == "drifted" else (22 if status == "missing" else 20)
        nodes[cid] = {
            "id": cid,
            "label": f"{obj.get('kind')}: {obj.get('metadata', {}).get('name')}",
            "file_type": "k8s_resource",
            "source_file": obj.get("_source", ""),
            "community": comm,
            "_origin": "state_graph",
            "properties": {
                "kind": obj.get("kind"),
                "apiVersion": obj.get("apiVersion"),
                "namespace": obj.get("metadata", {}).get("namespace", ""),
                "drift_status": status,
                "changes": drifted_map.get(did, []),
            },
        }
        for r in _annotation_roles(obj):
            for vid, vd in vault_desired.items():
                if vd.get("kind") == "auth_role" and vd.get("name", "").endswith(f"/{r}"):
                    add_link(cid, "uses-vault-role", vid)

    for uid in unmanaged_set:
        cuid = _canonical_graphify_k8s_id(uid)
        if cuid not in nodes:
            parts = uid.split("/")
            nodes[cuid] = {
                "id": cuid,
                "label": f"Unmanaged: {parts[-1]}",
                "file_type": "k8s_resource",
                "source_file": "k8s-live",
                "community": 23,
                "_origin": "state_graph",
                "properties": {"drift_status": "unmanaged"},
            }

    vdrift = report.get("vault_drift") or {}
    v_drifted = {d["id"]: d["changes"] for d in vdrift.get("drifted", [])}
    v_missing = set(vdrift.get("missing", []))

    for vid, vd in vault_desired.items():
        status = "drifted" if vid in v_drifted else ("missing" if vid in v_missing else "in-sync")
        comm = 21 if status == "drifted" else (22 if status == "missing" else 20)
        nodes[vid] = {
            "id": vid,
            "label": f"Vault {vd['kind']}: {vd['name']}",
            "file_type": "vault_resource",
            "source_file": vd.get("file", ""),
            "community": comm,
            "_origin": "state_graph",
            "properties": {
                "kind": vd["kind"],
                "name": vd["name"],
                "namespace": vd.get("namespace", ""),
                "drift_status": status,
                "changes": v_drifted.get(vid, []),
            },
        }
        if vd["kind"] == "auth_role":
            payload = vd.get("payload") or {}
            names = payload.get("bound_service_account_names", [])
            nss = payload.get("bound_service_account_namespaces", [])
            for sa in names if isinstance(names, list) else [names]:
                for ns in nss if isinstance(nss, list) else [nss]:
                    sa_id = _canonical_graphify_k8s_id(f"v1/ServiceAccount/{ns}/{sa}")
                    if sa_id in nodes:
                        add_link(vid, "binds-serviceaccount", sa_id)
            for pol in payload.get("token_policies", []) if isinstance(payload.get("token_policies"), list) else []:
                pol_id = f"vault:{vd.get('namespace', '')}:policy:{pol}"
                if pol_id in nodes:
                    add_link(vid, "grants-policy", pol_id)

    for vuid in vdrift.get("unmanaged", []):
        if vuid not in nodes:
            nodes[vuid] = {
                "id": vuid,
                "label": f"Unmanaged Vault: {vuid.split(':')[-1]}",
                "file_type": "vault_resource",
                "source_file": "vault-live",
                "community": 23,
                "_origin": "state_graph",
                "properties": {"drift_status": "unmanaged"},
            }

    for idx, finding in enumerate(report.get("vault_lint", [])):
        fid = f"lint:{finding['rule']}:{idx}"
        ffile = finding.get("file", "")
        nodes[fid] = {
            "id": fid,
            "label": f"Lint [{finding['severity']}]: {finding['rule']}",
            "file_type": "vault_lint",
            "source_file": ffile,
            "community": 24,
            "_origin": "state_graph",
            "properties": finding,
        }
        if ffile:
            for vid, vd in vault_desired.items():
                if vd.get("file") == ffile and vid in nodes:
                    add_link(vid, "has-lint-finding", fid)

    for idx, xc in enumerate(report.get("cross_check", [])):
        xid = f"crosscheck:{xc['rule']}:{idx}"
        nodes[xid] = {
            "id": xid,
            "label": f"CrossCheck [{xc['severity']}]: {xc['rule']}",
            "file_type": "cross_check",
            "source_file": "cross-system",
            "community": 24,
            "_origin": "state_graph",
            "properties": xc,
        }

    return {
        "directed": True,
        "multigraph": False,
        "graph": {
            "name": "iac-vs-live-state-graph",
            "node_count": len(nodes),
            "edge_count": len(links),
        },
        "nodes": list(nodes.values()),
        "links": links,
        "hyperedges": [],
    }


# ------------------------------------------------------------------ CLI


def _current_context() -> str:
    res = subprocess.run(["kubectl", "config", "current-context"], capture_output=True, text=True)
    return res.stdout.strip() if res.returncode == 0 else ""


def _load_json(path: Optional[str]) -> Any:
    if not path:
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        sys.exit(f"cannot read live snapshot {path}: {e}")


def main() -> None:
    ap = argparse.ArgumentParser(description="IaC vs live state for Kubernetes and Vault (read-only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("lint", "drift", "health", "report"):
        p = sub.add_parser(name)
        p.add_argument("--k8s", nargs="*", default=[], help="manifest dirs/files (rendered YAML)")
        p.add_argument("--vault", help="vault_controller config dir (api_paths YAML)")
        p.add_argument("--vault-namespace", default="")
        p.add_argument("--context", help="kubectl context")
        p.add_argument(
            "--allow-prod-read", action="store_true", help="permit read-only access to a context named *prod*"
        )
        p.add_argument("--live-k8s", help="offline: JSON list of live objects instead of kubectl")
        p.add_argument("--live-vault", help="offline: JSON live Vault snapshot instead of the vault CLI")
        p.add_argument("--no-live-vault", action="store_true", help="skip live Vault reads (needs no token)")
        p.add_argument("--format", choices=("json", "graphify"), default="json", help="output schema format")
    args = ap.parse_args()

    offline_k8s = args.live_k8s is not None
    ctx = args.context or ("" if offline_k8s else _current_context())
    if ctx and "prod" in ctx.lower() and not args.allow_prod_read and not offline_k8s:
        sys.exit(
            f"refusing: kubectl context '{ctx}' looks like production; pass --allow-prod-read for read-only access"
        )

    report: Dict[str, Any] = {"kubectl_context": ctx or None}
    kd = load_k8s_desired(args.k8s) if args.k8s else {}
    vd = load_vault_desired(Path(args.vault)) if args.vault else {}
    if args.cmd in ("lint", "report") and args.vault:
        report["vault_lint"] = lint_vault(Path(args.vault))
    live_k8s: List[Dict[str, Any]] = []
    if args.cmd in ("drift", "report", "health"):
        runner = _kubectl_runner(args.context)
        if args.cmd in ("drift", "report") and kd:
            live_k8s = _load_json(args.live_k8s) if offline_k8s else fetch_k8s_live(desired_scope(kd), runner)
            report["k8s_drift"] = diff_k8s(kd, live_k8s)
        if args.cmd in ("health", "report"):
            report["cluster_health"] = cluster_health(
                _load_json(args.live_k8s) if offline_k8s else fetch_health_objs(runner)
            )
    vlive = None
    if args.cmd in ("drift", "report") and vd and not args.no_live_vault:
        vlive = _load_json(args.live_vault) if args.live_vault else fetch_vault_live(args.vault_namespace)
        report["vault_drift"] = diff_vault(vd, vlive, args.vault_namespace)
    if args.cmd in ("drift", "report") and vd and kd:
        report["cross_check"] = cross_check(vd, kd, live_k8s, vlive)
    out_obj = report_to_graphify(report, kd, vd, live_k8s) if args.format == "graphify" else report
    print(json.dumps(out_obj, indent=2, default=str))


if __name__ == "__main__":
    main()
