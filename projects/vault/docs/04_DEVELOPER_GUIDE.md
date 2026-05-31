# Developer Guide

## Technical Deep-Dive & API Resource Anatomy

To make the platform completely deterministic, the Python core uses a declarative JSON schema format that maps exactly to Vault's structural components. Below is an explicit breakdown of the structural components, featuring production-grade configuration blocks and the core, zero-dependency Python orchestration execution code.

### 1. Configuration Manifesto: `config/vault_blueprint.json`
This manifest serves as the definitive source of truth for the target cluster state. It explicitly defines auth methods, secret engines, and fine-grained ACL access controls.

```json
{
  "$schema": "https://internal.platform.infra/schemas/vault-blueprint.v1.json",
  "auth_methods": [
    {
      "path": "approle",
      "type": "approle",
      "description": "Core machine-to-machine authentication backend for microservices",
      "config": {
        "default_lease_ttl": "3600s",
        "max_lease_ttl": "86400s"
      }
    }
  ],
  "secret_engines": [
    {
      "path": "kv-v2/payment-gateway",
      "type": "kv",
      "description": "PCI-compliant storage for financial service orchestration tokens",
      "options": {
        "version": "2"
      }
    },
    {
      "path": "transit/core-encryption",
      "type": "transit",
      "description": "High-throughput cryptographic operations for PII data protection"
    }
  ],
  "policies": [
    {
      "name": "payment-processor-read",
      "rules": "path \"kv-v2/data/payment-gateway/*\" { capabilities =[\"read\"] }\npath \"transit/encrypt/core-encryption\" { capabilities = [\"update\"] }"
    }
  ]
}
```

### 2. Core Python Orchestration Engine: `bin/cluster_reconciler.py`
This script contains the core orchestration logic. Built completely on top of the Python standard library, it enforces idempotency by verifying live cluster states against the blueprint before issuing mutation updates.

```python
#!/usr/bin/env python3
"""
Principal Platform Engineering Suite: Vault Reconciler Core.
Establishes stateless, idempotent configurations by evaluating target schemas
directly against active Vault HTTP API endpoints.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List

class VaultClient:
    """Zero-dependency HTTP client wrapper for advanced Vault API interactions."""
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token

    def _request(self, method: str, path: str, payload: Any = None) -> Dict[str, Any]:
        url = f"{self.base_url}/v1/{path.lstrip('/')}"
        headers = {
            "X-Vault-Token": self.token,
            "Content-Type": "application/json"
        }
       
        data = json.dumps(payload).encode('utf-8') if payload else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
       
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 204:
                    return {}
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404 and method == "GET":
                return {}
            error_msg = e.read().decode('utf-8')
            print(f"[-] API Error [{e.code}] on {method} {url}: {error_msg}", file=sys.stderr)
            raise

    def get(self, path: str) -> Dict[str, Any]:
        return self._request("GET", path)

    def put(self, path: str, payload: Any) -> Dict[str, Any]:
        return self._request("PUT", path, payload)


class ClusterReconciler:
    """Idempotency engine analyzing drift between config definitions and active clusters."""
    def __init__(self, client: VaultClient):
        self.client = client

    def reconcile_secret_engines(self, target_engines: List[Dict[str, Any]]) -> None:
        """Aligns live secret engines with defined configurations, avoiding structural overrides."""
        print("[*] Reconciling Secret Engines...")
       
        live_mounts = self.client.get("sys/mounts")
        if "data" in live_mounts:
            live_mounts = live_mounts["data"]

        for engine in target_engines:
            mount_path = f"{engine['path'].rstrip('/')}/"
           
            if mount_path in live_mounts:
                print(f"[+] Engine path '{mount_path}' is active. Verification complete.")
                continue
           
            print(f"[!] Path '{mount_path}' not found. Initializing engine creation payload...")
            payload = {
                "type": engine["type"],
                "description": engine.get("description", "Managed by Python Automation Suite"),
                "options": engine.get("options", {})
            }
            self.client.put(f"sys/mounts/{mount_path}", payload)
            print(f"[──>] Successfully mounted backend path: {mount_path}")

    def reconcile_policies(self, target_policies: List[Dict[str, Any]]) -> None:
        """Enforces precise access control policies by analyzing and updating matching configurations."""
        print("[*] Reconciling Access Control Policies...")
       
        for policy in target_policies:
            name = policy["name"]
            target_rules = policy["rules"].strip()
           
            live_policy = self.client.get(f"sys/policies/acl/{name}")
            live_rules = live_policy.get("data", {}).get("policy", "").strip() if live_policy else ""
           
            if live_rules == target_rules:
                print(f"[+] ACL Policy '{name}' matches target schema exactly. Skipping update.")
                continue
               
            print(f"[!] Policy '{name}' has drifted or is new. Updating ACL rules...")
            self.client.put(f"sys/policies/acl/{name}", {"policy": target_rules})
            print(f"[──>] Successfully updated policy: {name}")


def main():
    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")
    config_path = os.getenv("VAULT_CONFIG_PATH", "config/vault_blueprint.json")

    if not vault_addr or not vault_token:
        print("[-] Critical Failure: VAULT_ADDR and VAULT_TOKEN environment variables must be defined.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(config_path):
        print(f"[-] Config blueprint file not found at path: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, "r") as f:
        blueprint = json.load(f)

    client = VaultClient(vault_addr, vault_token)
    reconciler = ClusterReconciler(client)

    try:
        reconciler.reconcile_secret_engines(blueprint.get("secret_engines", []))
        reconciler.reconcile_policies(blueprint.get("policies", []))
        print("[+] Reconciled complete cluster status successfully.")
    except Exception as e:
        print(f"[-] Automation run halted due to processing exception: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
```

**Real-World Scale Factor: How Massive Deployments Handle Splitting Architecture**
In high-scale architectures, organizations do not load a single monolithic `vault_blueprint.json` on every run. Instead, they leverage file-system segmentation. The core automation loader scans a directory structure like `config/auth/*.json` and `config/engines/**/*.json`. This approach allows individual development teams to own and modify distinct files without overlapping lines or generating merge conflicts, while keeping the reconciliation engine stateless and fast.

---

## The Definitive Integration Test Framework

To guarantee runtime safety without relying on live production environments, engineers can implement local integration testing. This approach uses Python's testing frameworks alongside local ephemeral dev containers to validate configurations before deployment.

### The Automated Test Suite: `tests/test_integration.py`
This test suite runs in isolation, spawning a real Vault dev server instance, loading configuration blueprints, running the custom reconciler engine, and verifying that the cluster state updates correctly.

```python
import os
import time
import subprocess
import pytest
from bin.cluster_reconciler import VaultClient, ClusterReconciler

@pytest.fixture(scope="module")
def local_vault_server():
    """Spawns an isolated local ephemeral Vault instance running in standard Dev Mode."""
    dev_token = "test-root-automation-token"
    listen_addr = "127.0.0.1:8201"
   
    proc = subprocess.Popen(
        ["vault", "server", "-dev", f"-dev-root-token-id={dev_token}", f"-dev-listen-address={listen_addr}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(1.5)
   
    os.environ["VAULT_ADDR"] = f"http://{listen_addr}"
    os.environ["VAULT_TOKEN"] = dev_token
   
    yield f"http://{listen_addr}", dev_token
   
    proc.terminate()
    proc.wait()

def test_reconciliation_lifecycle(local_vault_server):
    """Verifies that the reconciler engine provisions components and enforces configuration states correctly."""
    base_url, token = local_vault_server
    client = VaultClient(base_url, token)
    reconciler = ClusterReconciler(client)
   
    mock_blueprint = {
        "secret_engines": [
            {
                "path": "kv-test-engine",
                "type": "kv",
                "description": "Integration Test Pipeline Engine Target",
                "options": {"version": "2"}
            }
        ],
        "policies": [
            {
                "name": "integration-test-policy",
                "rules": "path \"kv-test-engine/data/*\" { capabilities = [\"read\"] }"
            }
        ]
    }
   
    reconciler.reconcile_secret_engines(mock_blueprint["secret_engines"])
    reconciler.reconcile_policies(mock_blueprint["policies"])
   
    live_mounts = client.get("sys/mounts")
    assert "kv-test-engine/" in live_mounts["data"]
    assert live_mounts["data"]["kv-test-engine/"]["type"] == "kv"
   
    live_policy = client.get("sys/policies/acl/integration-test-policy")
    assert "capabilities = [\"read\"]" in live_policy["data"]["policy"]
   
    try:
        reconciler.reconcile_secret_engines(mock_blueprint["secret_engines"])
        reconciler.reconcile_policies(mock_blueprint["policies"])
    except Exception as exc:
        pytest.fail(f"Subsequent reconciliation pass failed, breaking idempotency constraints: {exc}")
```
