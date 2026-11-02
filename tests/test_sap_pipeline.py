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
        self.assertEqual(len(parents), len(CONSOLIDATION_MAP), "Expected all consolidated Core Parent skills")
        total_units = sum(len(p["procedural_units"]) for p in parents)
        self.assertGreater(total_units, 100, "Expected >100 procedural units across Core Parent skills")

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
        self.assertTrue(verify_be_bindings(unit_text, contract, {"namespace": "default", "pod_name": "web-0"}))
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

    # ---- Reference corpus integrity (references/**/*.md are passive runbooks, reachable from SKILL.md) ----

    @staticmethod
    def _strip_fences(text: str) -> str:
        import re

        return re.sub(r"```.*?```", "", text, flags=re.S)

    def _ref_files(self):
        return sorted((REPO_ROOT / ".agent/skills").glob("*/references/**/*.md"))

    def test_07_reference_purity(self):
        """references/**/*.md must not carry SKILL.md identity (line-1 frontmatter, bootstrap loop, {SKILL_DIR})."""
        offenders = []
        for f in self._ref_files():
            text = f.read_text(encoding="utf-8")
            body = self._strip_fences(text)
            if text.startswith("---\nname:"):
                offenders.append(f"{f}: line-1 frontmatter")
            if "Knowledge Bootstrap" in body and "MANDATORY" in body:
                offenders.append(f"{f}: Knowledge Bootstrap loop")
            if "{SKILL_DIR}" in body or "{skill_dir}" in body:
                offenders.append(f"{f}: unexpanded SKILL_DIR placeholder")
        self.assertEqual(offenders, [], "Reference purity violations")

    def test_08_reference_links_resolve_and_are_reachable(self):
        """Every .md path outside code fences resolves; every reference is reachable from SKILL.md in <=2 hops."""
        import re

        skills_dir = REPO_ROOT / ".agent/skills"
        path_re = re.compile(r"(?<![\w/])((?:\.{1,2}/|\.agent/skills/[\w-]+/)?(?:references/)?[\w./-]+\.md)\b")

        def resolve(token: str, src: Path, skill: Path):
            for base in (REPO_ROOT, skill, src.parent):
                cand = (base / token).resolve()
                if cand.is_file():
                    return cand
            return None

        broken, unreachable = [], []
        for skill in sorted(d for d in skills_dir.iterdir() if (d / "SKILL.md").is_file()):
            refs = {p.resolve() for p in skill.glob("references/**/*.md")}
            seen, frontier = set(), {(skill / "SKILL.md").resolve()}
            for _hop in range(3):  # SKILL.md -> hop1 -> hop2
                nxt = set()
                for src in frontier:
                    for tok in path_re.findall(self._strip_fences(src.read_text(encoding="utf-8"))):
                        if "references/" not in tok and src.name == "SKILL.md":
                            continue
                        hit = resolve(tok, src, skill)
                        if hit is None:
                            if "references/" in tok:
                                broken.append(f"{src.relative_to(REPO_ROOT)} -> {tok}")
                            continue
                        if hit in refs and hit not in seen:
                            nxt.add(hit)
                seen |= nxt
                frontier = nxt
            unreachable += [str(p.relative_to(REPO_ROOT)) for p in sorted(refs - seen)]
        self.assertEqual(sorted(set(broken)), [], "Broken reference links outside code fences")
        self.assertEqual(unreachable, [], "References unreachable from SKILL.md within 2 hops")

    def test_09_action_template_placeholders_are_declared(self):
        """Every {placeholder} in contract action_templates must be a declared required/optional input."""
        import re

        import yaml

        problems = []
        for cf in sorted((REPO_ROOT / ".agent/contracts").glob("*.yaml")):
            c = yaml.safe_load(cf.read_text(encoding="utf-8"))
            declared = set(c["input_schema"].get("required", {})) | set(c["input_schema"].get("optional", {}))
            self.assertNotIn("skill_dir", declared, f"{cf.name}: skill_dir is an index-time constant, not an input")
            for t in c.get("action_templates", []):
                if re.search(r"\bls\b[^|]*references/", t):
                    problems.append(f"{cf.name}: blind ls of references/")
                problems += [
                    f"{cf.name}: undeclared {{{m}}}" for m in re.findall(r"\{([a-z_]+)\}", t) if m not in declared
                ]
        self.assertEqual(problems, [], "Action template defects")

    def test_10_volatile_facts_are_sourced_dated_and_fresh(self):
        """Every row under '## Volatile facts' needs an ISO as-of date within max_age_days, a source URL on the
        skill's authoritative-host allowlist (.agent/sources.yaml), and a search query."""
        import datetime
        import re

        import yaml

        reg = yaml.safe_load((REPO_ROOT / ".agent/sources.yaml").read_text(encoding="utf-8"))
        max_age = int(reg["max_age_days"])
        today = datetime.date.today()
        url_re = re.compile(r"https?://[^\s)|`]+")
        problems = []
        for f in self._ref_files():
            text = f.read_text(encoding="utf-8")
            m = re.search(r"^## Volatile facts.*?(?=^## |\Z)", text, flags=re.S | re.M)
            if not m:
                continue
            skill = f.relative_to(REPO_ROOT / ".agent/skills").parts[0]
            allowed = reg["skills"].get(skill)
            rel = f.relative_to(REPO_ROOT).as_posix()
            if not allowed:
                problems.append(f"{rel}: skill {skill} has no entry in .agent/sources.yaml")
                continue
            rows = [ln for ln in m.group(0).splitlines() if ln.startswith("|")][2:]  # drop header + separator
            if not rows:
                problems.append(f"{rel}: Volatile facts section has no rows")
            for row in rows:
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                if len(cells) != 4:
                    problems.append(f"{rel}: row needs 4 columns: {row[:60]}")
                    continue
                claim, asof, source, query = cells
                try:
                    age = (today - datetime.date.fromisoformat(asof)).days
                    if age < 0 or age > max_age:
                        problems.append(f"{rel}: as-of {asof} outside 0..{max_age} days ({claim[:40]})")
                except ValueError:
                    problems.append(f"{rel}: bad as-of date '{asof}' ({claim[:40]})")
                urls = url_re.findall(source)
                if not urls:
                    problems.append(f"{rel}: no source URL ({claim[:40]})")
                for u in urls:
                    hostpath = re.sub(r"^https?://", "", u)
                    if not any(hostpath == a or hostpath.startswith(a + "/") for a in allowed):
                        problems.append(f"{rel}: source host not allowlisted for {skill}: {u}")
                if not query.strip("` "):
                    problems.append(f"{rel}: missing search query ({claim[:40]})")
        self.assertEqual(problems, [], "Volatile facts defects")

    def test_11_risk_gate_scans_every_command_field(self):
        """Oversight-loosening flags are rejected wherever they appear, including probes and verify (no field
        escapes compute_risk). A declared side effect plus a confirm precondition still permits a flagged command."""
        from scripts.sap.verifier import compute_risk

        base = {"action_templates": ["echo ok"], "side_effects": {}, "preconditions": []}
        for field in ("action_templates", "probes", "verify"):
            c = dict(base)
            c[field] = ["terraform apply -auto-approve"]
            risk, reasons = compute_risk(c)
            self.assertGreaterEqual(risk, 0.80, field)
            self.assertIn("oversight_loosening_flag", reasons, field)
        lease = dict(base, action_templates=["git push --force-with-lease origin feat/x"])
        self.assertEqual(compute_risk(lease)[0], 0.0)
        allowed = {
            "action_templates": ["apt-get install --yes jq"],
            "side_effects": {"oversight_loosening_flag": "installs jq"},
            "preconditions": ["User must confirm the install"],
        }
        self.assertEqual(compute_risk(allowed)[0], 0.0)

    def test_12_no_emoji_and_script_paths_resolve(self):
        """AGENTS.md bans emoji. Every `scripts/...` or `.agent/skills/...` file path named in a reference or
        SKILL.md must exist (a path that does not exist makes the agent run a command that cannot work)."""
        import re

        emoji = re.compile("[\U0001f300-\U0001faff\u2600-\u27bf\u2b50\u2b55\ufe0f]")
        path_re = re.compile(
            r"(?<![\w/.-])(\.agent/skills/[\w./-]+|scripts/[\w./-]+\.(?:py|sh|mjs|js|ts|json|yaml|yml|txt)(?![\w]|\.\w)|bin/[\w./-]+\.(?:py|sh)(?![\w]|\.\w))"
        )
        skills = REPO_ROOT / ".agent/skills"
        problems = []
        targets = list(self._ref_files()) + list(skills.glob("*/SKILL.md"))
        for f in targets:
            if f.suffix != ".md":
                continue
            text = f.read_text(encoding="utf-8")
            rel = f.relative_to(REPO_ROOT)
            if emoji.search(text):
                problems.append(f"{rel}: contains emoji")
            skill = f.relative_to(skills).parts[0]
            for m in set(path_re.findall(text)):
                cand = m.rstrip(".,:;)")
                if any(c in cand for c in "<>*{}$"):
                    continue
                options = [REPO_ROOT / cand, skills / skill / cand, skills / skill / "scripts" / Path(cand).name]
                if not any(o.exists() for o in options):
                    problems.append(f"{rel}: missing path {cand}")
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
