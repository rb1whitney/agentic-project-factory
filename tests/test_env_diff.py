#!/usr/bin/env python3
"""state_graph env-diff across tfvars, Helm values, Kustomize overlays and Hiera layers."""

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-code-map" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import state_graph as sg  # noqa: E402


def w(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class EnvDiffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_tfvars(self) -> None:
        w(self.root, "vars/dev.tfvars", 'replicas = 1\nregion = "us"\ndb_password = "a"\n')
        w(self.root, "vars/prod.tfvars", 'replicas = 3\nregion = "us"\nextra = true\ndb_password = "b"\n')
        d = sg.env_diff(self.root, "dev", "prod")["layers"]["vars/{env}.tfvars"]
        self.assertEqual(d["differ"]["replicas"], {"dev": "1", "prod": "3"})
        self.assertEqual(d["only_in_prod"], {"extra": "true"})
        self.assertEqual(d["differ"]["db_password"], {"dev": "[REDACTED]", "prod": "[REDACTED]"})
        self.assertNotIn("region", d["differ"])

    def test_helm_values_nested(self) -> None:
        w(self.root, "chart/values-dev.yaml", "resources:\n  limits:\n    cpu: 100m\nimage: {tag: a}\n")
        w(self.root, "chart/values-prod.yaml", "resources:\n  limits:\n    cpu: 500m\nonly: x\n")
        d = sg.env_diff(self.root, "dev", "prod")["layers"]["chart/values-{env}.yaml"]
        self.assertEqual(d["differ"]["resources.limits.cpu"], {"dev": "100m", "prod": "500m"})
        self.assertEqual(d["only_in_dev"], {"image.tag": "a"})
        self.assertEqual(d["only_in_prod"], {"only": "x"})

    def test_hiera_and_kustomize_and_missing_layer(self) -> None:
        w(self.root, "hieradata/appenv/dev/cos.yaml", "cos::port: 80\n")
        w(self.root, "hieradata/appenv/prod/cos.yaml", "cos::port: 443\n")
        w(self.root, "k/overlays/dev/patch.yaml", "spec: {replicas: 1}\n")
        res = sg.env_diff(self.root, "dev", "prod")["layers"]
        self.assertEqual(res["hieradata/appenv/{env}/cos.yaml"]["differ"]["cos::port"], {"dev": 80, "prod": 443})
        self.assertEqual(res["k/overlays/{env}/patch.yaml"], {"only_in": "dev"})

    def test_identical_layers_omitted_and_table(self) -> None:
        w(self.root, "vars/dev.tfvars", "a = 1\n")
        w(self.root, "vars/prod.tfvars", "a = 1\n")
        res = sg.env_diff(self.root, "dev", "prod")
        self.assertEqual(res["layers"], {})
        self.assertEqual(sg.env_diff_table(res), "no differences")


if __name__ == "__main__":
    unittest.main()
