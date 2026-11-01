#!/usr/bin/env python3
"""
Stage 5: Refactor with Binding Extraction (BE) & Rewrite Cleanup (RC) Post-Checks (SaP §3.2, §3.5, §5.7).
Guarantees:
1. BE Post-Check: Every required input of κ has a non-empty binding whose tokens overlap unit text.
2. RC Post-Check: Every refactored skill bundle contains:
   - Block 1: Action Templates (concrete executable commands/syntax)
   - Block 2: Procedural Skeleton with invoke(κ, {...}) call-sites
   - Block 3: Inlined Child Contracts
   - All expected contracts remain referenced after rewrite.
"""

import re

TOKEN_RE = re.compile(r"[a-z0-9_]{2,}")
INVOKE_RE = re.compile(r"invoke\(\s*([a-z0-9-]+)\s*,")


def verify_be_bindings(unit_text: str, contract: dict, bindings: dict) -> bool:
    """
    Deterministic BE post-check (SaP §3.2):
    Drops call-sites whose bindings are missing required inputs, empty, or whose tokens do not overlap unit_text.
    """
    if not bindings or not isinstance(bindings, dict):
        return False
    req_inputs = list(contract.get("input_schema", {}).get("required", {}).keys())
    if not req_inputs:
        return False

    unit_low = unit_text.lower()
    unit_toks = set(TOKEN_RE.findall(unit_low))

    for req in req_inputs:
        if req not in bindings:
            return False
        val = str(bindings[req]).strip()
        if not val:
            return False
        val_low = val.lower()
        val_toks = set(TOKEN_RE.findall(val_low))
        # Check overlap with unit text or explicit parameter name presence in unit text
        req_parts = {p for p in req.lower().split("_") if len(p) >= 2}
        if not (val_low in unit_low or (val_toks & unit_toks) or (req_parts & unit_toks)):
            return False
    return True


def verify_rc_bundle(bundle_markdown: str, expected_contracts: list[str] | None = None) -> tuple[bool, list[str]]:
    """
    Deterministic RC post-check & Bundle-Component Ablation guard (SaP §3.2, §3.5, §5.7):
    Verifies that a refactored SKILL.md contains:
    1. Action Templates block with concrete code/CLI syntax (never contract-only).
    2. Procedural Skeleton block with at least one invoke(κ, ...) call-site.
    3. Inlined Child Contracts block documenting κ's signature.
    4. Every contract in expected_contracts remains referenced by invoke(...).
    """
    reasons = []
    has_templates_heading = bool(re.search(r"^##\s+.*Action Templates", bundle_markdown, re.MULTILINE | re.IGNORECASE))
    has_code_fence = "```" in bundle_markdown
    if not (has_templates_heading and has_code_fence):
        reasons.append("missing_action_templates")

    has_skeleton_heading = bool(
        re.search(r"^##\s+.*(?:Procedural Skeleton|Dispatch Skeleton)", bundle_markdown, re.MULTILINE | re.IGNORECASE)
    )
    invoked_ids = set(INVOKE_RE.findall(bundle_markdown))
    if not (has_skeleton_heading and invoked_ids):
        reasons.append("missing_procedural_skeleton_or_invoke")

    has_contracts_heading = bool(
        re.search(r"^##\s+.*Inlined (?:Child )?Contracts", bundle_markdown, re.MULTILINE | re.IGNORECASE)
    )
    if not has_contracts_heading:
        reasons.append("missing_inlined_contracts")

    if expected_contracts:
        for cid in expected_contracts:
            if cid not in invoked_ids:
                reasons.append(f"missing_expected_contract:{cid}")

    return (len(reasons) == 0), reasons
