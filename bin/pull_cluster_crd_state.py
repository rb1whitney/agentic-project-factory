#!/usr/bin/env python3
"""
pull_cluster_crd_state.py
Pulls all CRDs from Kubernetes API, iterates through versions (v1, v2, v3, etc.),
fetches instances of each resource across the cluster, and outputs a normalized cluster state map.
"""

import json
import os
import subprocess
from typing import Any, Dict, List

KUBECONFIG = os.environ.get("KUBECONFIG", "/etc/rancher/k3s/k3s.yaml")


def run_kubectl(args: List[str]) -> Any:
    env = os.environ.copy()
    env["KUBECONFIG"] = KUBECONFIG
    cmd = ["kubectl"] + args
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    if res.returncode != 0:
        return None
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return res.stdout.strip()


def get_all_crds() -> List[Dict[str, Any]]:
    data = run_kubectl(["get", "crd", "-o", "json"])
    if not data or "items" not in data:
        return []

    crd_specs = []
    for item in data["items"]:
        metadata = item.get("metadata", {})
        spec = item.get("spec", {})
        name = metadata.get("name")
        group = spec.get("group")
        names = spec.get("names", {})
        plural = names.get("plural")
        kind = names.get("kind")
        scope = spec.get("scope")

        versions = [v.get("name") for v in spec.get("versions", []) if v.get("served", True)]

        crd_specs.append({
            "crd_name": name,
            "group": group,
            "plural": plural,
            "kind": kind,
            "scope": scope,
            "versions": versions,
        })
    return crd_specs


def get_crd_instances(plural: str, group: str, version: str) -> List[Dict[str, Any]]:
    resource_path = f"{plural}.{version}.{group}"
    data = run_kubectl(["get", resource_path, "-A", "-o", "json"])
    if not data or "items" not in data:
        return []

    extracted_items = []
    for item in data["items"]:
        meta = item.get("metadata", {})
        extracted_items.append({
            "apiVersion": item.get("apiVersion"),
            "kind": item.get("kind"),
            "name": meta.get("name"),
            "namespace": meta.get("namespace"),
            "uid": meta.get("uid"),
            "generation": meta.get("generation"),
            "resourceVersion": meta.get("resourceVersion"),
            "creationTimestamp": meta.get("creationTimestamp"),
            "spec": item.get("spec", {}),
            "status": item.get("status", {})
        })
    return extracted_items


def build_cluster_state() -> Dict[str, Any]:
    crds = get_all_crds()
    cluster_state: Dict[str, Any] = {
        "crd_count": len(crds),
        "resources": {}
    }

    for crd in crds:
        crd_name = crd["crd_name"]
        group = crd["group"]
        plural = crd["plural"]

        crd_entry = {
            "group": group,
            "kind": crd["kind"],
            "scope": crd["scope"],
            "versions": crd["versions"],
            "instances_by_version": {}
        }

        total_instances = 0
        for ver in crd["versions"]:
            instances = get_crd_instances(plural, group, ver)
            if instances:
                crd_entry["instances_by_version"][ver] = instances
                total_instances += len(instances)

        if total_instances > 0:
            cluster_state["resources"][crd_name] = crd_entry

    return cluster_state


def main():
    state = build_cluster_state()
    summary = {
        "total_crds": state["crd_count"],
        "crds_with_active_instances": len(state["resources"]),
        "active_kinds": {
            k: {
                "kind": v["kind"],
                "versions": list(v["instances_by_version"].keys()),
                "count": sum(len(items) for items in v["instances_by_version"].values())
            }
            for k, v in state["resources"].items()
        }
    }

    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".agent", "cluster_crd_state.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    print(json.dumps(summary, indent=2))
    print(f"\nFull cluster state written to: {output_path}")


if __name__ == "__main__":
    main()
