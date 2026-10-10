#!/usr/bin/env python3
"""
local_extract.py - Normalize ast-grep JSON match streams into lean domain records.
Covers: Java, Kubernetes, Crossplane v2, Terraform HCL, and Vault.
Defaults to self-contained rules located within the skill scripts directory.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "sgconfig.yml"


def run_ast_grep_scan(config_path: Path, targets: List[str]) -> List[Dict[str, Any]]:
    cmd = ["ast-grep", "scan", "--json", "-c", str(config_path)] + targets
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        if not proc.stdout.strip():
            return []
        return json.loads(proc.stdout)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"ast-grep scan failed: {e.stderr}\n")
        return []
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Failed to parse ast-grep output: {e}\n")
        return []


def normalize_record(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rule_id = match.get("ruleId", "")
    file_path = match.get("file", "")
    meta_vars = match.get("metaVariables", {}).get("single", {})

    extracted_data = {}
    for var_key, var_val in meta_vars.items():
        extracted_data[var_key.lower()] = var_val.get("text", "")

    scope_map = {
        "extract-spring-controller": ("controller_declaration", "web_layer"),
        "extract-spring-service": ("service_declaration", "service_layer"),
        "extract-k8s-resource": ("k8s_resource", "k8s_infrastructure"),
        "extract-crossplane-xrd": ("crossplane_xrd", "crossplane_v2"),
        "extract-crossplane-composition": ("crossplane_composition", "crossplane_v2"),
        "extract-tf-attribute": ("terraform_attribute", "cloud_infra"),
        "extract-vault-api-path": ("vault_api_path", "vault_security"),
    }

    record_type, source_scope = scope_map.get(rule_id, (rule_id, "general"))
    source_name = (
        extracted_data.get("path")
        or extracted_data.get("class")
        or extracted_data.get("name")
        or extracted_data.get("kind")
        or Path(file_path).stem
    )

    line_no = match.get("range", {}).get("start", {}).get("line", 0) + 1
    record_id = f"{file_path}#{source_name}:{line_no}"

    return {
        "record_type": record_type,
        "record_id": record_id,
        "path": file_path,
        "source_name": source_name,
        "source_scope": source_scope,
        "line": line_no,
        "extracted_data": extracted_data,
    }


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else [
        "projects/cloud-boot-app",
        "projects/vault_controller"
    ]
    config_file = DEFAULT_CONFIG

    matches = run_ast_grep_scan(config_file, targets)
    records = []
    for m in matches:
        rec = normalize_record(m)
        if rec:
            records.append(rec)

    output = {"records": records, "total": len(records)}
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
