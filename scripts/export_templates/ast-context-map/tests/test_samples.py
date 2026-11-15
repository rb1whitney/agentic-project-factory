import json
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
K8S = ROOT / "examples" / "k8s-sample"
VAULT = ROOT / "examples" / "vault-sample"


def run(script: str, *args) -> str:
    cmd = [sys.executable, str(SCRIPTS / script), *[str(a) for a in args]]
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def test_vault_lint_flags_each_bad_item_and_only_those():
    findings = json.loads(run("state_graph.py", "lint", "--vault", VAULT))["vault_lint"]
    assert sorted(f["rule"] for f in findings) == [
        "insecure-tls",
        "mount-ttl-over-1h",
        "plaintext-secret",
        "policy-read-write-mix",
        "transit-key-exportable",
    ]
    text = json.dumps(findings)
    assert "payments-admin" in text  # the bad policy
    assert "payments-reader" not in text  # the clean policy
    assert "api_key" not in text  # the Transit-encrypted value


def test_k8s_drift_reports_missing_drifted_and_unmanaged():
    out = json.loads(run("state_graph.py", "drift", "--k8s", K8S / "manifests", "--live-k8s", K8S / "live-k8s.json"))[
        "k8s_drift"
    ]
    assert out["missing"] == ["networking.k8s.io/v1/Ingress/payments/payments-api"]
    assert out["unmanaged"] == ["apps/v1/Deployment/payments/legacy-worker"]
    changed = {c["path"] for d in out["drifted"] for c in d["changes"]}
    assert {"spec.replicas", "spec.template.spec.containers[api].image"} <= changed


def test_vault_drift_reports_missing_mount_and_drifted_policy():
    out = json.loads(run("state_graph.py", "drift", "--vault", VAULT, "--live-vault", VAULT / "live-vault.json"))[
        "vault_drift"
    ]
    assert out["missing"] == ["vault::mount:transit"]
    assert [d["id"] for d in out["drifted"]] == ["vault::policy:payments-admin"]


def test_offline_graph_extraction_builds_graph(tmp_path):
    out = tmp_path / "graph.json"
    run("k8s_graphify_extract.py", "--live-k8s", K8S / "live-k8s.json", "--manifests", K8S / "manifests", "--out", out)
    ids = {n["id"] for n in json.loads(out.read_text())["nodes"]}
    assert "k8s:apps/Deployment/payments/legacy-worker" in ids
    assert len(ids) == 3


def test_extraction_strips_secret_values_and_writes_private_file(tmp_path):
    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "db", "namespace": "payments"},
        "data": {"password": "c3VwZXItc2VjcmV0LXZhbHVl"},
    }
    container = {"name": "c", "image": "x", "env": [{"name": "TOKEN", "value": "hunter2-plain-value"}]}
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "web", "namespace": "payments"},
        "spec": {"template": {"spec": {"containers": [container]}}},
    }
    snapshot = tmp_path / "live.json"
    snapshot.write_text(json.dumps([secret, deployment]))
    out = tmp_path / "graph.json"
    run("k8s_graphify_extract.py", "--live-k8s", snapshot, "--out", out)
    text = out.read_text()
    assert "c3VwZXItc2VjcmV0LXZhbHVl" not in text
    assert "hunter2-plain-value" not in text
    if os.name == "posix":
        assert stat.S_IMODE(out.stat().st_mode) == 0o600
