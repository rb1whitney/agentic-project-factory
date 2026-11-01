#!/usr/bin/env python3
"""Terraform typed nodes (graph_builder) and the provisions-k8s bridge (k8s_graphify_extract)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / ".agent" / "skills"
sys.path.insert(0, str(ROOT / "skill-code-map" / "scripts"))
sys.path.insert(0, str(ROOT / "skill-graphify" / "scripts"))

import graph_builder as gb  # noqa: E402
import k8s_graphify_extract as kg  # noqa: E402

TF = """
provider "google" {
  alias = "meta"
}

variable "env" {
  default = "dev"
}

variable "db_password" {
  default = "hunter2"
}

module "net" {
  source  = "terraform-google-modules/network/google"
  version = "~> 9.0"
}

resource "helm_release" "grafana" {
  name       = "grafana"
  namespace  = "operations"
  chart      = "grafana"
  repository = "https://grafana.github.io/helm-charts"
}

resource "kubernetes_deployment" "api" {
  metadata {
    name      = "api"
    namespace = "app"
  }
}

resource "kubernetes_namespace" "ops" {
  metadata {
    name = "operations"
  }
}

resource "kubernetes_service" "dyn" {
  metadata {
    name = "${var.env}-svc"
  }
}
"""


def build(tmp: Path) -> dict:
    (tmp / "main.tf").write_text(TF)
    (tmp / "vars").mkdir()
    (tmp / "vars" / "prod.tfvars").write_text('env = "prod"\ndb_password = "s3cret"\n')
    mj = tmp / ".terraform" / "modules"
    mj.mkdir(parents=True)
    (mj / "modules.json").write_text(
        json.dumps(
            {"Modules": [{"Key": "net", "Source": "registry.terraform.io/x/network/google", "Version": "9.1.0"}]}
        )
    )
    return gb.GraphBuilder(str(tmp)).build_graph()


class TerraformNodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.nodes = build(Path(self.tmp.name))["nodes"]
        self.addCleanup(self.tmp.cleanup)

    def test_helm_and_kubernetes_resources(self) -> None:
        h = self.nodes["resource:helm_release/grafana"]
        self.assertEqual((h["name"], h["namespace"], h["chart"]), ("grafana", "operations", "grafana"))
        d = self.nodes["resource:kubernetes_deployment/api"]
        self.assertEqual((d["k8s_name"], d["k8s_namespace"]), ("api", "app"))

    def test_interpolation_left_unresolved(self) -> None:
        self.assertNotIn("k8s_name", self.nodes["resource:kubernetes_service/dyn"])

    def test_module_resolved_version_and_provider_alias(self) -> None:
        m = self.nodes["module:net"]
        self.assertEqual(m["version"], "~> 9.0")
        self.assertEqual(m["resolved_version"], "9.1.0")
        self.assertIn("provider:google.meta", self.nodes)

    def test_tfvars_bindings_and_redaction(self) -> None:
        self.assertEqual(self.nodes["tfvar:vars/prod.tfvars:env"]["value"], '"prod"')
        self.assertEqual(self.nodes["tfvar:vars/prod.tfvars:db_password"]["value"], "[REDACTED]")
        self.assertNotIn("default", self.nodes["variable:db_password"])


class BridgeTests(unittest.TestCase):
    def test_bridge_links_live_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            base = gb.to_graphify(build(Path(d)))
        live = kg.build_graphify_k8s_graph(
            [
                {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": "operations"}},
                {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {"name": "grafana-alloy", "namespace": "operations"},
                },
                {"apiVersion": "v1", "kind": "Service", "metadata": {"name": "other", "namespace": "operations"}},
                {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "api", "namespace": "app"}},
            ]
        )
        merged = kg.merge_graphify_graphs(base, live)
        rels = {(lk["source"], lk["relation"], lk["target"]) for lk in merged["links"]}
        h = "resource:helm_release/grafana"
        self.assertIn((h, "provisions-k8s", "k8s:core/Namespace/_cluster_/operations"), rels)
        self.assertIn((h, "provisions-k8s", "k8s:apps/Deployment/operations/grafana-alloy"), rels)
        self.assertNotIn((h, "provisions-k8s", "k8s:core/Service/operations/other"), rels)
        self.assertIn(("resource:kubernetes_deployment/api", "provisions-k8s", "k8s:apps/Deployment/app/api"), rels)
        self.assertIn(
            ("resource:kubernetes_namespace/ops", "provisions-k8s", "k8s:core/Namespace/_cluster_/operations"), rels
        )


if __name__ == "__main__":
    unittest.main()
