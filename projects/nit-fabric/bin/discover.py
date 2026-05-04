import json
import logging
import sys
import argparse
import subprocess
from typing import Dict, Any, List

# --- SRE Configuration: Professional Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] nit-fabric.discovery: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("nit-fabric.discovery")

class CloudDiscoverer:
    def __init__(self, mode: str = "mock"):
        self.mode = mode

    def discover_all(self) -> Dict[str, Any]:
        if self.mode == "mock":
            logger.info("Running in MOCK mode. Returning synthetic truth-report.")
            return self._get_mock_data()
        
        context = {
            "aws_cidrs": [],
            "gcp_cidrs": [],
            "aws_s3_buckets": [],
            "gcp_instances": [],
            "vpcs": [],
            "gke_clusters": [],
            "gcp_subnets": [],
            "rules": []
        }

        if self.mode == "cli" or self.mode == "live":
            logger.info(f"Initiating {self.mode.upper()} discovery sequence...")
            context["aws_cidrs"] = self._aws_get_cidrs()
            context["aws_s3_buckets"] = self._aws_get_s3()
            context["gcp_instances"] = self._gcp_get_instances()
            context["gke_clusters"] = self._gcp_get_gke()
            context["vpcs"] = self._aws_get_vpcs_with_endpoints()
            context["gcp_subnets"] = self._gcp_get_subnets()
        
        return context

    def _run_cli(self, cmd: List[str]) -> str:
        logger.debug(f"Executing CLI command: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except Exception as e:
            logger.debug(f"CLI Command failed: {cmd}. Error: {e}")
            return ""

    def _aws_get_cidrs(self) -> List[str]:
        vpc_out = self._run_cli(["aws", "ec2", "describe-vpcs", "--query", "Vpcs[*].CidrBlock", "--output", "json"])
        subnet_out = self._run_cli(["aws", "ec2", "describe-subnets", "--query", "Subnets[*].CidrBlock", "--output", "json"])
        vpcs = json.loads(vpc_out) if vpc_out else []
        subnets = json.loads(subnet_out) if subnet_out else []
        return list(set(vpcs + subnets))

    def _aws_get_vpcs_with_endpoints(self) -> List[Dict[str, Any]]:
        vpcs_out = self._run_cli(["aws", "ec2", "describe-vpcs", "--query", "Vpcs[*].VpcId", "--output", "json"])
        vpc_ids = json.loads(vpcs_out) if vpcs_out else []
        results = []
        for vpc_id in vpc_ids:
            endpoints_out = self._run_cli(["aws", "ec2", "describe-vpc-endpoints", "--filters", f"Name=vpc-id,Values={vpc_id}", "--query", "VpcEndpoints[*].{Service:ServiceName,Type:VpcEndpointType,DnsEnabled:PrivateDnsEnabled}", "--output", "json"])
            endpoints = json.loads(endpoints_out) if endpoints_out else []
            results.append({"id": vpc_id, "endpoints": endpoints})
        return results

    def _aws_get_s3(self) -> List[Dict[str, Any]]:
        buckets_out = self._run_cli(["aws", "s3api", "list-buckets", "--query", "Buckets[*].Name", "--output", "json"])
        buckets = json.loads(buckets_out) if buckets_out else []
        results = []
        for b in buckets:
            pab_out = self._run_cli(["aws", "s3api", "get-public-access-block", "--bucket", b, "--output", "json"])
            has_pab = pab_out != ""
            results.append({"name": b, "public_access": not has_pab})
        return results

    def _gcp_get_subnets(self) -> List[Dict[str, Any]]:
        output = self._run_cli(["gcloud", "compute", "networks", "subnets", "list", "--format=json"])
        data = json.loads(output) if output else []
        return [{"name": s["name"], "private_google_access": s.get("privateIpGoogleAccess", False), "region": s["region"]} for s in data]

    def _gcp_get_instances(self) -> List[Dict[str, Any]]:
        output = self._run_cli(["gcloud", "compute", "instances", "list", "--format=json"])
        data = json.loads(output) if output else []
        results = []
        for i in data:
            has_external = False
            for ni in i.get("networkInterfaces", []):
                for ac in ni.get("accessConfigs", []):
                    if ac.get("type") == "ONE_TO_ONE_NAT":
                        has_external = True
                        break
            results.append({"name": i["name"], "has_external_ip": has_external, "zone": i["zone"].split("/")[-1]})
        return results

    def _gcp_get_gke(self) -> List[Dict[str, Any]]:
        output = self._run_cli(["gcloud", "container", "clusters", "list", "--format=json"])
        data = json.loads(output) if output else []
        results = []
        for c in data:
            results.append({
                "name": c["name"],
                "location": c["location"],
                "workload_identity_enabled": "workloadIdentityConfig" in c,
                "node_pools": [np["name"] for np in c.get("nodePools", [])]
            })
        return results

    def _get_mock_data(self) -> Dict[str, Any]:
        return {
            "aws_cidrs": ["10.0.0.0/16", "10.0.1.0/24"],
            "gcp_cidrs": ["10.1.0.0/16", "192.168.1.0/24"],
            "aws_s3_buckets": [{"name": "prod-public-bucket", "public_access": True}],
            "gcp_instances": [{"name": "insecure-instance", "has_external_ip": True, "zone": "us-central1-a"}],
            "vpcs": [{"id": "vpc-001", "endpoints": [{"Service": "s3", "Type": "Interface", "DnsEnabled": False}]}],
            "gke_clusters": [{
                "name": "legacy-cluster", 
                "location": "us-central1",
                "workload_identity_enabled": False,
                "node_pools": ["default-pool", "highmem-pool"]
            }],
            "gcp_subnets": [{"name": "prod-subnet", "private_google_access": False, "region": "us-central1"}]
        }

def main():
    parser = argparse.ArgumentParser(description="nit-fabric High-Resolution Discoverer")
    parser.add_argument("--mode", choices=["mock", "cli", "terraform"], default="mock", help="Discovery mode")
    parser.add_argument("--output", default="context.json", help="Output file")
    parser.add_argument("--verbose", action="store_true", help="Show raw CLI commands being executed")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    discoverer = CloudDiscoverer(mode=args.mode)
    truth_report = discoverer.discover_all()

    with open(args.output, "w") as f:
        json.dump(truth_report, f, indent=2)
    
    logger.info(f"Discovery complete. Context archived to {args.output}")

if __name__ == "__main__":
    main()
