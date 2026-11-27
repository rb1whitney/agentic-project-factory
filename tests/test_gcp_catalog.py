#!/usr/bin/env python3
"""Unit tests for skill-code-map/scripts/gcp_catalog.py (offline fixtures, no GCP API)."""

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-code-map" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import gcp_catalog as gc  # noqa: E402

SAMPLE_ASSETS = [
    {
        "name": "//compute.googleapis.com/projects/p1/global/networks/vpc1",
        "assetType": "compute.googleapis.com/Network",
        "project": "projects/111",
        "displayName": "vpc1",
        "location": "global",
        "parentFullResourceName": "//cloudresourcemanager.googleapis.com/projects/p1",
    },
    {
        "name": "//compute.googleapis.com/projects/p1/regions/us-central1/subnetworks/sub1",
        "assetType": "compute.googleapis.com/Subnetwork",
        "project": "projects/111",
        "displayName": "sub1",
        "location": "us-central1",
        "parentFullResourceName": "//compute.googleapis.com/projects/p1/global/networks/vpc1",
        "additionalAttributes": {
            "network": "//compute.googleapis.com/projects/p1/global/networks/vpc1",
        },
    },
    {
        "name": "//container.googleapis.com/projects/p1/locations/us-central1/clusters/gke1",
        "assetType": "container.googleapis.com/Cluster",
        "project": "projects/111",
        "displayName": "gke1",
        "location": "us-central1",
        "parentFullResourceName": "//cloudresourcemanager.googleapis.com/projects/p1",
        "kmsKey": "projects/p1/locations/us-central1/keyRings/kr1/cryptoKeys/gke-key",
        "additionalAttributes": {
            "subnetwork": "//compute.googleapis.com/projects/p1/regions/us-central1/subnetworks/sub1",
        },
    },
    {
        "name": "//cloudkms.googleapis.com/projects/p1/locations/us-central1/keyRings/kr1/cryptoKeys/gke-key",
        "assetType": "cloudkms.googleapis.com/CryptoKey",
        "project": "projects/111",
        "displayName": "gke-key",
        "location": "us-central1",
        "parentFullResourceName": "//cloudkms.googleapis.com/projects/p1/locations/us-central1/keyRings/kr1",
    },
    {
        "name": "//secretmanager.googleapis.com/projects/p1/secrets/edge-gateway",
        "assetType": "secretmanager.googleapis.com/Secret",
        "project": "projects/111",
        "displayName": "edge-gateway",
        "location": "global",
        "additionalAttributes": {"payload": "SUPER_SECRET_SHOULD_BE_STRIPPED"},
    },
]

SAMPLE_IAM = [
    {
        "resource": "//secretmanager.googleapis.com/projects/p1/secrets/edge-gateway",
        "assetType": "secretmanager.googleapis.com/Secret",
        "policy": {
            "bindings": [
                {
                    "role": "roles/secretmanager.secretAccessor",
                    "members": ["serviceAccount:eso-wi@p1.iam.gserviceaccount.com"],
                }
            ]
        },
    }
]


class TestGcpCatalog(unittest.TestCase):
    def test_redacts_sensitive_fields(self):
        redacted = gc.redact_asset(SAMPLE_ASSETS[4])
        serialized = json.dumps(redacted)
        self.assertNotIn("SUPER_SECRET_SHOULD_BE_STRIPPED", serialized)
        self.assertEqual(redacted["displayName"], "edge-gateway")

    def test_builds_graphify_nodes_and_edges(self):
        graph = gc.build_graphify(SAMPLE_ASSETS, SAMPLE_IAM, project_id="p1")
        node_ids = {n["id"] for n in graph["nodes"]}
        self.assertIn("gcp:compute.googleapis.com/Network/vpc1", node_ids)
        self.assertIn("gcp:container.googleapis.com/Cluster/gke1", node_ids)
        self.assertIn("gcp:cloudkms.googleapis.com/CryptoKey/gke-key", node_ids)

        rels = {(e["source"], e["relation"], e["target"]) for e in graph["links"]}
        self.assertIn(
            (
                "gcp:compute.googleapis.com/Network/vpc1",
                "contains",
                "gcp:compute.googleapis.com/Subnetwork/sub1",
            ),
            rels,
        )
        self.assertIn(
            (
                "gcp:container.googleapis.com/Cluster/gke1",
                "encrypted-by-kms",
                "gcp:cloudkms.googleapis.com/CryptoKey/gke-key",
            ),
            rels,
        )
        self.assertIn(
            (
                "gcp:iam/Member/serviceAccount:eso-wi@p1.iam.gserviceaccount.com",
                "grants-iam-role",
                "gcp:secretmanager.googleapis.com/Secret/edge-gateway",
            ),
            rels,
        )

    def test_walks_resource_data_references(self):
        cai_resources = [
            {
                "name": "//compute.googleapis.com/projects/p1/global/networks/vpc1",
                "assetType": "compute.googleapis.com/Network",
                "resource": {"location": "global", "data": {"name": "vpc1"}},
            },
            {
                "name": "//compute.googleapis.com/projects/p1/regions/us-central1/subnetworks/sub1",
                "assetType": "compute.googleapis.com/Subnetwork",
                "resource": {
                    "location": "us-central1",
                    "data": {
                        "name": "sub1",
                        "network": "https://www.googleapis.com/compute/v1/projects/p1/global/networks/vpc1",
                        "selfLink": "https://www.googleapis.com/compute/v1/projects/p1/regions/us-central1/subnetworks/sub1",
                    },
                },
            },
            {
                "name": "//compute.googleapis.com/projects/p1/regions/us-central1/targetPools/tp1",
                "assetType": "compute.googleapis.com/TargetPool",
                "resource": {"location": "us-central1", "data": {"name": "tp1"}},
            },
            {
                "name": "//compute.googleapis.com/projects/p1/regions/us-central1/forwardingRules/fr1",
                "assetType": "compute.googleapis.com/ForwardingRule",
                "resource": {
                    "location": "us-central1",
                    "data": {
                        "name": "fr1",
                        "target": "https://www.googleapis.com/compute/v1/projects/p1/regions/us-central1/targetPools/tp1",
                    },
                },
            },
        ]
        graph = gc.build_graphify(cai_resources, [], project_id="p1")
        rels = {(e["source"], e["relation"], e["target"]) for e in graph["links"]}
        self.assertIn(
            (
                "gcp:compute.googleapis.com/Subnetwork/sub1",
                "uses-network",
                "gcp:compute.googleapis.com/Network/vpc1",
            ),
            rels,
        )
        self.assertIn(
            (
                "gcp:compute.googleapis.com/ForwardingRule/fr1",
                "targets",
                "gcp:compute.googleapis.com/TargetPool/tp1",
            ),
            rels,
        )

    def test_atomic_write_permissions_0600(self):
        graph = gc.build_graphify(SAMPLE_ASSETS, [], project_id="p1")
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "gcp-graph.json"
            gc.write_graph_atomic(out_path, graph)
            mode = stat.S_IMODE(os.stat(out_path).st_mode)
            self.assertEqual(mode, 0o600)
            loaded = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(len(loaded["nodes"]), len(graph["nodes"]))


if __name__ == "__main__":
    unittest.main()
