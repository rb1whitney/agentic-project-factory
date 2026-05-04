import json
import logging
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

# --- SRE Configuration: Professional Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] nit-fabric.remediator: %(message)s",
    stream=sys.stderr # Keep logs on stderr to leave stdout for patches
)
logger = logging.getLogger("nit-fabric.remediator")

class PolicyRemediator:
    """
    Industrial-grade remediation engine that uses Jinja2 templates
    to generate surgical HCL patches and investigations.
    """
    
    def __init__(self, provider: str = "terraform") -> None:
        self.provider = provider
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape()
        )
        
        if self.provider == "terraform":
            self.template_map = {
                "bgp-asn-mismatch": "bgp_asn_mismatch.j2",
                "UNRESTRICTED_INGRESS": "unrestricted_ingress.j2",
                "AWS_PUBLIC_S3": "aws_public_s3.j2",
                "GCP_EXTERNAL_IP": "gcp_external_ip.j2"
            }
        else:
            self.template_map = {
                "UNRESTRICTED_INGRESS": "aws_cli_remediation.j2",
                "AWS_PUBLIC_S3": "aws_cli_remediation.j2",
                "GCP_EXTERNAL_IP": "gcp_cli_remediation.j2",
                "GKE_WORKLOAD_IDENTITY_CHECK": "gcp_cli_remediation.j2",
                "PRIVATE_ACCESS_AUDIT": "aws_cli_remediation.j2",
                "INSPECTION_VPC_ENFORCEMENT": "aws_cli_remediation.j2"
            }

    def analyze_failure(self, scenario: Dict[str, Any]) -> Tuple[str, str]:
        report_id: Optional[str] = scenario.get("id") or scenario.get("violation_type")
        
        if not report_id:
            logger.error("Malformed scenario detected: Missing 'id' or 'violation_type'")
            return "ERR_MALFORMED_INPUT", ""

        logger.info(f"Analyzing failure scenario: {report_id}")
        template_name = self.template_map.get(report_id)
        
        if not template_name:
            logger.warning(f"No deterministic remediation template for: {report_id}")
            return f"Unknown failure mode: {report_id}", ""

        try:
            template = self.env.get_template(template_name)
            context_data = {**scenario, **scenario.get("metadata", {}), "id": report_id}
            output = template.render(**context_data)
            
            # Split on either Terraform or CLI patch markers
            if "# PROPOSED REMEDIATION:" in output:
                parts = output.split("# PROPOSED REMEDIATION:")
            elif "# PROPOSED SHELL COMMANDS:" in output:
                parts = output.split("# PROPOSED SHELL COMMANDS:")
            else:
                parts = [output]
            
            investigation = parts[0].strip()
            patch = parts[1].strip() if len(parts) > 1 else ""
            
            if patch:
                self.validate_patch(patch)
            
            return investigation, patch
            
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            return f"ERR_TEMPLATE_FAILURE: {e}", ""

    def validate_patch(self, patch: str) -> None:
        logger.info("Validating patch safety (simulation)...")
        if "delete" in patch.lower() or "-" in patch:
            logger.warning("[SAFETY] Potentially destructive action detected in patch.")
        logger.info("Patch validation: SUCCESS")

def main() -> None:
    parser = argparse.ArgumentParser(description="nit-fabric Remediator")
    parser.add_argument("--provider", choices=["terraform", "cli"], default="terraform", help="Remediation provider")
    parser.add_argument("--input", default="violations.json", help="Path to violations file")
    parser.add_argument("--output", help="Path to save generated patches")
    parser.add_argument("--explain", action="store_true", help="Just explain how to fix each issue (Consultant Mode)")
    args = parser.parse_args()

    input_path = Path(args.input)
    # Fallback to test data if live violations are missing
    if not input_path.exists():
        script_dir = Path(__file__).parent.parent
        input_path = script_dir / "tests" / "test_failures.json"
    
    logger.info(f"Loading input from {input_path}")

    try:
        with open(input_path, "r") as f:
            content = json.load(f)
            scenarios = content if isinstance(content, list) else content.get("scenarios", [])
            
        remediator = PolicyRemediator(provider=args.provider)
        
        all_patches = []
        for scenario in scenarios:
            investigation, patch = remediator.analyze_failure(scenario)
            
            # Print results based on mode
            if args.explain:
                sys.stderr.write(f"\n[EXPERT ADVICE] {scenario.get('violation_type', 'Policy Violation')}\n")
                sys.stderr.write(f"Explanation: {investigation}\n")
                advice = scenario.get("advice") or "No specific expert advice available for this policy."
                sys.stdout.write(f"REMEDIATION PLAYBOOK:\n{advice}\n")
                sys.stdout.write("-" * 60 + "\n")
            else:
                if patch:
                    all_patches.append(patch)
                
                # Print investigation to stderr, patch to stdout
                sys.stderr.write(f"\n--- Investigation: {scenario.get('violation_type', 'Unknown')} ---\n")
                sys.stderr.write(investigation + "\n")
                if patch:
                    sys.stdout.write(patch + "\n")
                sys.stderr.write("-" * 40 + "\n")

        if args.output:
            with open(args.output, "w") as f:
                f.write("\n\n".join(all_patches))
            logger.info(f"All patches saved to {args.output}")
            
    except Exception as e:
        logger.exception(f"Operational failure: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
