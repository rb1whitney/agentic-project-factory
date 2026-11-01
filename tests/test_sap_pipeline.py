#!/usr/bin/env python3
"""
TDD Test Suite for Skill-as-Pseudocode (SaP) Compiler, 4-Check Verifier,
30 Synthetic Negative Controls, BE/RC Post-Checks, and Bundle-Component Integrity.
Reference: Li et al., arXiv:2605.27955v2 (Skill-as-Pseudocode).
"""

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


class TestSaPPipeline(unittest.TestCase):
    def test_01_schemas_exist_and_validate(self):
        """contract.schema.json and updated agent.schema.json must exist and validate canonical records."""
        import jsonschema

        contract_schema_path = REPO_ROOT / ".agent/adapters/schemas/contract.schema.json"
        agent_schema_path = REPO_ROOT / ".agent/adapters/schemas/agent.schema.json"
        self.assertTrue(contract_schema_path.exists(), "Missing contract.schema.json")
        self.assertTrue(agent_schema_path.exists(), "Missing agent.schema.json")

        contract_schema = json.loads(contract_schema_path.read_text(encoding="utf-8"))
        sample_contract = {
            "id": "k8s-pod-triage",
            "trigger": "Pod status in Pending, CrashLoopBackOff, Error, ImagePullBackOff",
            "input_schema": {
                "required": {"namespace": "string", "pod_name": "string"},
                "optional": {"container_name": "string"},
            },
            "output_schema": {
                "root_cause_category": "string",
                "remediation_cmd": "string",
            },
            "preconditions": ["kubectl context verified"],
            "postconditions": ["root cause isolated before mutation"],
            "resources": ["{SKILL_DIR}/references/PodCrashLoopBackOff.md"],
            "side_effects": {"filesystem": "none", "network": "read-only K8s API"},
            "source_parents": ["skill-kubernetes", "skill-sre-investigation"],
            "action_templates": [
                "kubectl get pods -n {namespace} | bin/rtk",
                "kubectl logs {pod_name} -n {namespace} | bin/rtk",
            ],
        }
        jsonschema.validate(instance=sample_contract, schema=contract_schema)

    def test_02_parser_extracts_procedural_units(self):
        """Stage 1 parser splits SKILL.md frontmatter and markdown headings into procedural units."""
        from scripts.sap.consolidate_skills import CONSOLIDATION_MAP
        from scripts.sap.parser import parse_skill_library

        skills_dir = REPO_ROOT / ".agent/skills"
        parents = [p for p in parse_skill_library(skills_dir) if p["name"] in CONSOLIDATION_MAP]
        self.assertEqual(len(parents), 13, "Expected all 13 consolidated Core Parent skills")
        total_units = sum(len(p["procedural_units"]) for p in parents)
        self.assertGreater(total_units, 100, "Expected >100 procedural units across 13 Core Parent skills")

        k8s_parent = next((p for p in parents if p["name"] == "skill-kubernetes"), None)
        self.assertIsNotNone(k8s_parent, "skill-kubernetes must be parsed")
        self.assertGreater(len(k8s_parent["procedural_units"]), 0)

    def test_03_verifier_four_checks_and_risk_gate(self):
        """Stage 4 verifier computes coverage, binding, replacement, risk and hard-rejects unsafe sinks."""
        from scripts.sap.verifier import verify_contract

        cluster_units = [
            {
                "parent": "skill-kubernetes",
                "heading": "Pod Status & Logistics",
                "text": "Check status of pods in target namespace. Command: kubectl get pods -n <namespace>. "
                "Logs: kubectl logs <pod_name> -n <namespace>. Isolate root_cause_category and remediation_cmd.",
                "code_blocks": ["kubectl get pods -n <namespace>", "kubectl logs <pod_name> -n <namespace>"],
            },
            {
                "parent": "skill-sre-investigation",
                "heading": "Pod Triage",
                "text": "Inspect pod_name in namespace via kubectl get pods -n <namespace> and kubectl logs <pod_name> "
                "to produce root_cause_category and remediation_cmd.",
                "code_blocks": ["kubectl get pods -n <namespace>"],
            },
        ]
        valid_contract = {
            "id": "k8s-pod-triage",
            "trigger": "Check status of pods in namespace and inspect logs",
            "input_schema": {"required": {"namespace": "string", "pod_name": "string"}, "optional": {}},
            "output_schema": {"root_cause_category": "string", "remediation_cmd": "string"},
            "preconditions": ["kubectl context verified"],
            "postconditions": ["root cause isolated"],
            "resources": [],
            "side_effects": {"filesystem": "none", "network": "read-only K8s API"},
            "source_parents": ["skill-kubernetes", "skill-sre-investigation"],
            "action_templates": [
                "kubectl get pods -n {namespace} | bin/rtk",
                "kubectl logs {pod_name} -n {namespace} | bin/rtk",
            ],
        }
        profile = verify_contract(cluster_units, valid_contract)
        self.assertGreaterEqual(profile["coverage"], 0.65)
        self.assertGreaterEqual(profile["binding"], 0.65)
        self.assertEqual(profile["replacement"], 1.0)
        self.assertEqual(profile["risk"], 0.0)
        self.assertEqual(profile["tier"], "auto_promote")

        # Unsafe contract with undeclared rm -rf must be hard-rejected by risk check
        unsafe_contract = dict(valid_contract)
        unsafe_contract["action_templates"] = ["rm -rf /tmp/cluster && git push origin master"]
        unsafe_profile = verify_contract(cluster_units, unsafe_contract)
        self.assertGreaterEqual(unsafe_profile["risk"], 0.80)
        self.assertEqual(unsafe_profile["tier"], "reject")
        self.assertIn("risk", unsafe_profile["rejection_reasons"])

    def test_04_negative_controls_zero_fp(self):
        """30 synthetic negative controls (10 B, 10 C, 10 D) must yield 0% FP."""
        from scripts.sap.verifier import evaluate_negative_controls, generate_negative_controls

        controls = generate_negative_controls(n_per_class=10)
        self.assertEqual(len(controls), 30)
        report = evaluate_negative_controls(controls, tau_auto=0.65, tau_rev=0.35)
        self.assertEqual(
            report["fp_rate"],
            0.0,
            f"Expected 0.0% FP on 30 negative controls, got {report['fp_rate']} ({report['promoted_ids']})",
        )

    def test_05_binding_extraction_and_rewrite_cleanup_post_checks(self):
        """BE post-check drops ungrounded bindings; RC post-check verifies templates + invoke + inlined contract."""
        from scripts.sap.refactor import verify_be_bindings, verify_rc_bundle

        contract = {
            "id": "k8s-pod-triage",
            "input_schema": {"required": {"namespace": "string", "pod_name": "string"}, "optional": {}},
        }
        unit_text = "Run kubectl get pods -n default and check pod_name web-0."
        self.assertTrue(
            verify_be_bindings(unit_text, contract, {"namespace": "default", "pod_name": "web-0"})
        )
        # Missing required input or token not overlapping unit text -> rejected
        self.assertFalse(
            verify_be_bindings(unit_text, contract, {"namespace": "nonexistent_token_xyz", "pod_name": "web-0"})
        )
        self.assertFalse(verify_be_bindings(unit_text, contract, {"namespace": "default"}))

        # Verify bundle structure (Block 1: Action Templates, Block 2: Procedural Skeleton, Block 3: Inlined Contracts)
        valid_bundle = """---
name: skill-test
description: Test skill
---
# Skill: skill-test
> NOTE: `invoke(...)` is structural pseudocode notation, not a shell binary.

## 1. Action Templates (Concrete How)
```bash
kubectl get pods -n {namespace} | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
1. diag <- invoke(k8s-pod-triage, {namespace: "<namespace>", pod_name: "<pod_name>"})
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: k8s-pod-triage`**: inputs `{namespace, pod_name}` -> outputs `{root_cause_category, remediation_cmd}`
"""
        rc_ok, reasons = verify_rc_bundle(valid_bundle, expected_contracts=["k8s-pod-triage"])
        self.assertTrue(rc_ok, f"Valid bundle failed RC check: {reasons}")

        # Bundle missing Action Templates (contract-only failure mode from Table 4) must fail RC check
        contract_only_bundle = """---
name: skill-test
description: Test skill
---
## 2. Procedural Skeleton
1. invoke(k8s-pod-triage, {namespace: "default", pod_name: "web-0"})
## 3. Inlined Child Contracts
- `κ: k8s-pod-triage`
"""
        rc_ok2, reasons2 = verify_rc_bundle(contract_only_bundle, expected_contracts=["k8s-pod-triage"])
        self.assertFalse(rc_ok2)
        self.assertIn("missing_action_templates", reasons2)

    def test_06_hierarchical_separation_and_live_corpus_integrity(self):
        """
        Verify live .agent/contracts/*.yaml, .agent/skills/*/SKILL.md, and .agent/agents/*.yaml:
        1. Child contracts live in .agent/contracts/*.yaml and pass 4-check verifier.
        2. Child contracts are NOT surfaced as standalone directories in .agent/skills/ (hierarchical separation).
        3. Every canonical agent in .agent/agents/*.yaml has a valid `contract` block and SaP prompt structure.
        4. Every skill in .agent/skills/*/SKILL.md passes RC bundle verification (Action Templates + invoke + Contract).
        """
        import yaml

        from scripts.sap.refactor import verify_rc_bundle
        from scripts.sap.verifier import verify_contract_catalog

        contracts_dir = REPO_ROOT / ".agent/contracts"
        skills_dir = REPO_ROOT / ".agent/skills"
        agents_dir = REPO_ROOT / ".agent/agents"

        self.assertTrue(contracts_dir.exists(), ".agent/contracts directory must exist")
        contract_files = sorted(contracts_dir.glob("*.yaml"))
        self.assertGreaterEqual(len(contract_files), 10, "Expected at least 10 promoted child contracts")

        catalog_report = verify_contract_catalog(contracts_dir, skills_dir)
        self.assertEqual(
            catalog_report["rejected_count"],
            0,
            f"All promoted contracts in .agent/contracts must pass verifier: {catalog_report['rejected']}",
        )

        # Hierarchical separation: no contract id may exist as a top-level skill directory
        from scripts.sap.consolidate_skills import CONSOLIDATION_MAP

        core_parents = list(CONSOLIDATION_MAP.keys())
        skill_names = {d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").is_file()}
        for cf in contract_files:
            cdata = yaml.safe_load(cf.read_text(encoding="utf-8"))
            self.assertNotIn(
                cdata["id"],
                skill_names,
                f"Hierarchical separation violation: child contract {cdata['id']} surfaced in .agent/skills/",
            )

        # Verify all 15 canonical agents have contract block + SaP sections + bind all 13 Core Parent skills
        agent_files = sorted(agents_dir.glob("*.yaml"))
        self.assertEqual(len(agent_files), 15)
        bound_skills = set()
        for af in agent_files:
            adata = yaml.safe_load(af.read_text(encoding="utf-8"))
            self.assertIn("contract", adata, f"Agent {af.name} missing 'contract' field")
            self.assertIn("Action Templates", adata["prompt"], f"Agent {af.name} prompt missing Action Templates")
            self.assertIn("invoke(", adata["prompt"], f"Agent {af.name} prompt missing invoke(...) skeleton")
            for s in adata.get("skills", []):
                self.assertIn(s, skill_names, f"Agent {af.name} binds nonexistent skill {s}")
                bound_skills.add(s)

        self.assertEqual(
            bound_skills,
            set(core_parents),
            f"Orphan Core Parent skills detected: {set(core_parents) - bound_skills}",
        )

        # Verify all 13 Core Parent skills have SaP bundle header
        for parent_name in core_parents:
            smd = skills_dir / parent_name / "SKILL.md"
            text = smd.read_text(encoding="utf-8")
            ok, reasons = verify_rc_bundle(text, expected_contracts=[])
            self.assertTrue(ok, f"Skill {smd} failed SaP RC bundle check: {reasons}")


if __name__ == "__main__":
    unittest.main()
