#!/usr/bin/env python3
"""
Stage 4: Deterministic 4-Check Verifier & Negative-Control Calibration (SaP §3.3, §3.4, §5.8).
Computes:
1. Coverage (w_c = 0.30): token recall of contract trigger/I-O strings against parent units.
2. Binding (w_b = 0.40): fraction of (parent, required_input) pairs where parent unit text binds the input.
3. Replacement (w_r = 0.30): fraction of parent units admitting invoke(κ) substitution without fence breakage.
4. Risk (w_s = 1.00): AST/regex scan for undeclared unsafe sinks (rm -rf, terraform destroy, git push, etc.).
   Hard-rejects at risk >= 0.80.
"""

import json
import re
from pathlib import Path

import yaml

TOKEN_RE = re.compile(r"[a-z0-9_]{2,}")

# Unsafe sinks that trigger hard rejection (risk >= 0.80) unless explicitly declared in side_effects + preconditions
UNSAFE_PATTERNS = [
    (re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f\b"), "destructive_rm_rf", 0.90),
    (re.compile(r"\bterraform\s+destroy\b"), "destructive_terraform_destroy", 0.90),
    (re.compile(r"\bgit\s+push\s+\S+\s+(?:master|main)\b"), "direct_push_to_main", 0.95),
    (re.compile(r"\bgh\s+pr\s+merge\b"), "autonomous_pr_merge", 0.95),
    (re.compile(r"\bsubprocess\.(?:run|Popen|call)\([^)]*shell\s*=\s*True"), "unsafe_subprocess_shell", 0.85),
    (re.compile(r"\beval\s*\("), "unsafe_eval", 0.85),
]

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "that",
    "this",
    "are",
    "via",
    "use",
    "using",
    "when",
    "string",
    "bool",
    "int",
    "list",
    "dict",
    "path",
    "enum",
    "none",
}


def _tokens(text: str) -> set[str]:
    return {t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS}


def _expand_snake_tokens(toks: set[str]) -> set[str]:
    expanded = set(toks)
    parts = [part for t in toks for part in t.split("_") if len(part) >= 3]
    expanded.update(parts)
    return expanded


def compute_coverage(cluster_units: list[dict], contract: dict) -> float:
    """Token recall of contract trigger + input_schema + output_schema keys against each parent's unit text."""
    if not cluster_units:
        return 0.0
    req_in = list(contract.get("input_schema", {}).get("required", {}).keys())
    opt_in = list(contract.get("input_schema", {}).get("optional", {}).keys())
    out_keys = list(contract.get("output_schema", {}).keys())
    contract_str = " ".join([contract.get("trigger", "")] + req_in + opt_in + out_keys)
    contract_toks = _tokens(contract_str)
    for k in req_in + out_keys:
        for part in k.lower().split("_"):
            if len(part) >= 3 and part not in STOPWORDS:
                contract_toks.add(part)
    if not contract_toks:
        return 0.0

    recalls = []
    for u in cluster_units:
        u_str = f"{u.get('heading', '')} {u.get('text', '')} {' '.join(u.get('code_blocks', []))}"
        expanded_u = _expand_snake_tokens(_tokens(u_str))
        hit = len(contract_toks & expanded_u)
        recalls.append(hit / len(contract_toks))
    return sum(recalls) / len(recalls)


def compute_binding(cluster_units: list[dict], contract: dict) -> float:
    """For each required input, fraction of (parent, input) pairs whose unit text overlaps input name or stem."""
    req_inputs = list(contract.get("input_schema", {}).get("required", {}).keys())
    if not cluster_units or not req_inputs:
        return 0.0

    total_pairs = len(cluster_units) * len(req_inputs)
    bound_pairs = 0
    for u in cluster_units:
        u_str = f"{u.get('heading', '')} {u.get('text', '')} {' '.join(u.get('code_blocks', []))}".lower()
        u_toks = _tokens(u_str)
        for inp in req_inputs:
            inp_low = inp.lower()
            parts = [p for p in inp_low.split("_") if len(p) >= 2 and p not in STOPWORDS]
            if inp_low in u_str or any(p in u_toks or p in u_str for p in parts):
                bound_pairs += 1
    return bound_pairs / total_pairs


def compute_replacement(cluster_units: list[dict], contract: dict) -> float:
    """Fraction of units admitting an invoke(κ, args) replacement while preserving balanced fences and valid id."""
    if not cluster_units:
        return 0.0
    cid = contract.get("id", "")
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", cid):
        return 0.0
    if not contract.get("action_templates"):
        return 0.0

    valid_units = 0
    for u in cluster_units:
        raw = u.get("text", "")
        # Fence balance check
        if raw.count("```") % 2 == 0:
            valid_units += 1
    return valid_units / len(cluster_units)


def compute_risk(contract: dict) -> tuple[float, list[str]]:
    """Scan contract action_templates and resources for unsafe sinks."""
    templates = "\n".join(contract.get("action_templates", []))
    resources = "\n".join(contract.get("resources", []))
    combined = f"{templates}\n{resources}"
    side_effects_str = json.dumps(contract.get("side_effects", {})).lower()
    preconds_str = " ".join(contract.get("preconditions", [])).lower()

    max_risk = 0.0
    reasons = []
    for rx, label, weight in UNSAFE_PATTERNS:
        if rx.search(combined):
            # Only allow if explicitly declared in side_effects AND user confirmation in preconditions
            if label in side_effects_str and "confirm" in preconds_str:
                continue
            max_risk = max(max_risk, weight)
            reasons.append(label)
    return max_risk, reasons


def verify_contract(
    cluster_units: list[dict],
    contract: dict,
    tau_auto: float = 0.65,
    tau_rev: float = 0.35,
) -> dict:
    """Run all 4 deterministic checks and return profile + 3-tier decision."""
    if contract.get("_extraction_failed"):
        return {
            "id": contract.get("id", "unknown"),
            "coverage": 0.0,
            "binding": 0.0,
            "replacement": 0.0,
            "risk": 0.0,
            "promotion_score": 0.0,
            "tier": "reject",
            "rejection_reasons": ["extraction_failed"],
        }

    coverage = compute_coverage(cluster_units, contract)
    binding = compute_binding(cluster_units, contract)
    replacement = compute_replacement(cluster_units, contract)
    risk, risk_reasons = compute_risk(contract)

    # Weights: w_b=0.40, w_c=0.30, w_r=0.30, w_s=1.00
    score = (0.40 * binding) + (0.30 * coverage) + (0.30 * replacement) - (1.00 * risk)

    rejection_reasons = []
    if risk >= 0.80:
        rejection_reasons.append("risk")
        rejection_reasons.extend(risk_reasons)
    if binding < 0.50:
        rejection_reasons.append("binding")
    if coverage < 0.45:
        rejection_reasons.append("coverage_recall")
    if replacement < 0.80:
        rejection_reasons.append("replacement")

    if risk >= 0.80 or rejection_reasons:
        tier = "reject" if (risk >= 0.80 or score < tau_rev or binding < 0.50 or coverage < 0.45) else "review"
    elif score >= tau_auto:
        tier = "auto_promote"
    elif score >= tau_rev:
        tier = "review"
    else:
        tier = "reject"

    return {
        "id": contract.get("id", "unknown"),
        "coverage": round(coverage, 4),
        "binding": round(binding, 4),
        "replacement": round(replacement, 4),
        "risk": round(risk, 4),
        "promotion_score": round(score, 4),
        "tier": tier,
        "rejection_reasons": rejection_reasons,
    }


def generate_negative_controls(n_per_class: int = 10) -> list[dict]:
    """
    Generate 30 synthetic negative controls across 3 single-library classes (SaP §3.4, §5.8, Appendix W.5):
    - B_same_domain_distinct: units from different (verb, object) frames forced into a cluster.
    - C_near_miss: same verb but mismatched object across parents (binding check fails per-parent).
    - D_swapped_contract: coherent cluster paired with a contract from a completely different cluster (coverage fails).
    """
    controls = []

    # Class B: same_domain_distinct
    for i in range(n_per_class):
        controls.append(
            {
                "control_id": f"B_same_domain_distinct_{i}",
                "class": "B_same_domain_distinct",
                "units": [
                    {
                        "parent": "skill-kubernetes",
                        "heading": f"Pod Logs {i}",
                        "text": "Fetch container logs via kubectl logs pod_alpha in namespace default.",
                        "code_blocks": ["kubectl logs pod_alpha -n default"],
                    },
                    {
                        "parent": "skill-certificate-manager",
                        "heading": f"ACME TLS Renewal {i}",
                        "text": "Rotate x509 certificate authority chain and PrivateKey Secret via certbot renew.",
                        "code_blocks": ["certbot renew --dns-cloudflare"],
                    },
                ],
                "contract": {
                    "id": f"neg-b-distinct-{i}",
                    "trigger": "Fetch pod logs and rotate x509 ACME certificate",
                    "input_schema": {
                        "required": {
                            "namespace": "string",
                            "pod_alpha": "string",
                            "acme_dns_zone": "string",
                            "x509_ca_bundle": "string",
                        },
                        "optional": {},
                    },
                    "output_schema": {"cert_serial": "string", "pod_exit_code": "string"},
                    "preconditions": [],
                    "postconditions": [],
                    "side_effects": {"filesystem": "none", "network": "read-only"},
                    "source_parents": ["skill-kubernetes", "skill-certificate-manager"],
                    "action_templates": ["kubectl logs {pod_alpha} -n {namespace}"],
                },
            }
        )

    # Class C: near_miss (same verb 'validate', disjoint required object slots per parent)
    for i in range(n_per_class):
        controls.append(
            {
                "control_id": f"C_near_miss_{i}",
                "class": "C_near_miss",
                "units": [
                    {
                        "parent": "skill-terraform",
                        "heading": f"Validate HCL {i}",
                        "text": "Validate terraform_module_dir and tfvars_file with terraform validate.",
                        "code_blocks": ["terraform validate"],
                    },
                    {
                        "parent": "skill-sql",
                        "heading": f"Validate SQL Schema {i}",
                        "text": "Validate postgres_dsn and migration_revision_id with alembic check.",
                        "code_blocks": ["alembic check"],
                    },
                ],
                "contract": {
                    "id": f"neg-c-nearmiss-{i}",
                    "trigger": "Validate configuration schema",
                    "input_schema": {
                        "required": {
                            "terraform_module_dir": "string",
                            "tfvars_file": "string",
                            "postgres_dsn": "string",
                            "migration_revision_id": "string",
                        },
                        "optional": {},
                    },
                    "output_schema": {"validation_status": "string"},
                    "preconditions": [],
                    "postconditions": [],
                    "side_effects": {"filesystem": "none", "network": "none"},
                    "source_parents": ["skill-terraform", "skill-sql"],
                    "action_templates": ["terraform validate {terraform_module_dir}"],
                },
            }
        )

    # Class D: swapped_contract (K8s cluster paired with SageMaker HyperPod training contract)
    for i in range(n_per_class):
        controls.append(
            {
                "control_id": f"D_swapped_contract_{i}",
                "class": "D_swapped_contract",
                "units": [
                    {
                        "parent": "skill-kubernetes",
                        "heading": f"K8s Service Discovery {i}",
                        "text": "Verify CoreDNS service_name resolution inside namespace using nslookup.",
                        "code_blocks": ["kubectl exec pod -- nslookup svc.cluster.local"],
                    },
                    {
                        "parent": "skill-network",
                        "heading": f"PrivateLink DNS {i}",
                        "text": "Check route53 private hosted zone DNS resolution for service_name.",
                        "code_blocks": ["dig service.internal"],
                    },
                ],
                "contract": {
                    "id": f"neg-d-swapped-{i}",
                    "trigger": "Launch SageMaker HyperPod LoRA fine-tuning job on FSx Lustre dataset",
                    "input_schema": {
                        "required": {
                            "hyperpod_cluster_arn": "string",
                            "lora_rank_alpha": "string",
                            "fsx_lustre_mount": "string",
                        },
                        "optional": {},
                    },
                    "output_schema": {"checkpoint_s3_uri": "string", "perplexity_loss": "string"},
                    "preconditions": [],
                    "postconditions": [],
                    "side_effects": {"filesystem": "none", "network": "sagemaker API"},
                    "source_parents": ["skill-aws-sagemaker"],
                    "action_templates": [
                        "aws sagemaker create-training-job --training-job-name {hyperpod_cluster_arn}"
                    ],
                },
            }
        )

    return controls


def evaluate_negative_controls(
    controls: list[dict],
    tau_auto: float = 0.65,
    tau_rev: float = 0.35,
) -> dict:
    promoted_ids = []
    results = []
    for ctrl in controls:
        prof = verify_contract(ctrl["units"], ctrl["contract"], tau_auto=tau_auto, tau_rev=tau_rev)
        if prof["tier"] == "auto_promote":
            promoted_ids.append(ctrl["control_id"])
        results.append({"control_id": ctrl["control_id"], "class": ctrl["class"], **prof})
    fp_rate = len(promoted_ids) / len(controls) if controls else 0.0
    return {
        "total": len(controls),
        "promoted_count": len(promoted_ids),
        "promoted_ids": promoted_ids,
        "fp_rate": fp_rate,
        "results": results,
    }


def _strip_sap_bundle(text: str) -> str:
    s_tag = "<!-- SAP_BUNDLE_START -->"
    e_tag = "<!-- SAP_BUNDLE_END -->"
    if s_tag in text and e_tag in text:
        return text[: text.index(s_tag)] + "\n" + text[text.index(e_tag) + len(e_tag) :]
    return text


def verify_contract_catalog(contracts_dir: Path, skills_dir: Path) -> dict:
    """Verify all promoted YAML contracts in .agent/contracts/ against their declared source_parents."""
    import jsonschema

    schema_path = contracts_dir.parent / "adapters/schemas/contract.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    promoted = []
    rejected = []
    for cf in sorted(contracts_dir.glob("*.yaml")):
        contract = yaml.safe_load(cf.read_text(encoding="utf-8"))
        jsonschema.validate(instance=contract, schema=schema)

        units = []
        for parent_name in contract.get("source_parents", []):
            skill_md = skills_dir / parent_name / "SKILL.md"
            if skill_md.exists():
                raw_text = _strip_sap_bundle(skill_md.read_text(encoding="utf-8"))
                units.append(
                    {
                        "parent": parent_name,
                        "heading": parent_name,
                        "text": raw_text,
                        "code_blocks": contract.get("action_templates", []),
                    }
                )
        prof = verify_contract(units, contract)
        if prof["tier"] == "auto_promote":
            promoted.append(prof)
        else:
            rejected.append(prof)

    return {
        "total": len(promoted) + len(rejected),
        "promoted_count": len(promoted),
        "rejected_count": len(rejected),
        "promoted": promoted,
        "rejected": rejected,
    }
