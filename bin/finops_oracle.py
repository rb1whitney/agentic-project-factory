import argparse
import functools
import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List

import boto3
import vertexai
from google.cloud import bigquery, securitycenter_v1
from vertexai.generative_models import GenerativeModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FOCUS 1.2 compliant CostRecord
@dataclass
class CostRecord:
    provider: str
    account_id: str
    resource_id: str
    availability_zone: str
    service_name: str
    net_unblended_cost: float
    currency: str
    timestamp: datetime

@dataclass
class DiscoveryRecord:
    resource_id: str
    provider: str
    service: str
    tags: Dict[str, str]
    last_active: datetime
    state: str = "unknown"

def retry_with_backoff(retries=5, backoff_in_seconds=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        logger.error(f"Max retries reached for {func.__name__}: {e}")
                        raise e
                    sleep = (backoff_in_seconds * 2 ** x + random.uniform(0, 1))
                    logger.warning(f"Retrying {func.__name__} in {sleep:.2f}s due to: {e}")
                    time.sleep(sleep)
                    x += 1
        return wrapper
    return decorator

class AWSIngestor:
    def __init__(self, database: str, table: str, output_location: str):
        self.athena = boto3.client('athena')
        self.database = database
        self.table = table
        self.output_location = output_location

    @retry_with_backoff()
    def query_cur_v2(self, query: str) -> List[CostRecord]:
        """Execute Athena v4 query on Iceberg v3 CUR v2 data"""
        response = self.athena.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': self.database},
            ResultConfiguration={'OutputLocation': self.output_location}
        )
        exec_id = response['QueryExecutionId']
        while True:
            status = self.athena.get_query_execution(QueryExecutionId=exec_id)
            state = status['QueryExecution']['Status']['State']
            if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                break
            time.sleep(2)
        if state != 'SUCCEEDED':
            raise Exception(f"Athena failed: {state}")

        paginator = self.athena.get_paginator('get_query_results')
        records = []
        for page in paginator.paginate(QueryExecutionId=exec_id):
            cols = [col['Name'] for col in page['ResultSet']['ResultSetMetadata']['ColumnInfo']]
            for row in page['ResultSet']['Rows']:
                vals = [v.get('VarCharValue', '') for v in row['Data']]
                if vals[0] == cols[0]:
                    continue  # Skip header
                d = dict(zip(cols, vals))
                records.append(CostRecord(
                    provider="aws", account_id=d.get('line_item_usage_account_id', ''),
                    resource_id=d.get('line_item_resource_id', ''),
                    availability_zone=d.get('line_item_availability_zone', ''),
                    service_name=d.get('line_item_product_code', ''),
                    net_unblended_cost=float(d.get('line_item_net_unblended_cost', 0.0)),
                    currency=d.get('pricing_currency', 'USD'),
                    timestamp=datetime.fromisoformat(d.get('line_item_usage_start_date').replace('Z', '+00:00'))
                ))
        return records

class AWSDiscovery:
    def __init__(self):
        self.explorer = boto3.client('resource-explorer-2')

    def discover_resources(self, query: str = "*") -> List[DiscoveryRecord]:
        """Aggregate resources via Resource Explorer V2 (2026 Standard)"""
        records = []
        try:
            for page in self.explorer.get_paginator('search').paginate(QueryString=query):
                for res in page.get('Resources', []):
                    tags = {
                        t['Key']: t['Value']
                        for prop in res.get('Properties', []) if prop['Name'] == 'tags'
                        for t in prop['Data']
                    }
                    records.append(DiscoveryRecord(
                        resource_id=res['Arn'], provider="aws", service=res['Service'],
                        tags=tags, last_active=res.get('LastReportedAt', datetime.now(timezone.utc))
                    ))
        except Exception as e:
            logger.error(f"AWS Discovery failed: {e}")
        return records

class GCPIngestor:
    def __init__(self, project_id: str, dataset_id: str, table_id: str):
        self.bq = bigquery.Client(project=project_id)
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_id = table_id

    def query_billing(self) -> List[CostRecord]:
        query = (
            f"SELECT * FROM `{self.project_id}.{self.dataset_id}.{self.table_id}` "
            f"WHERE usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)"
        )
        return [CostRecord(
            provider="gcp", account_id=r.billing_account_id, resource_id=r.resource.id or '',
            availability_zone=r.location.zone or '', service_name=r.service.description,
            net_unblended_cost=float(r.cost), currency=r.currency, timestamp=r.usage_start_time
        ) for r in self.bq.query(query).result()]

class GCPDiscovery:
    def __init__(self, project_id: str):
        self.client = securitycenter_v1.SecurityCenterClient()
        self.project_id = project_id

    def discover_resources(self) -> List[DiscoveryRecord]:
        """Retrieve findings from SCC Agentless Scanning"""
        parent = f"projects/{self.project_id}/sources/-"
        finding_filter = 'state="ACTIVE" AND (category="DISK_IS_UNUSED" OR category="UNATTACHED_IP_ADDRESS")'
        records = []
        try:
            for result in self.client.list_findings(request={"parent": parent, "filter": finding_filter}):
                f = result.finding
                records.append(DiscoveryRecord(
                    resource_id=f.resource_name, provider="gcp", service=f.category,
                    tags={}, last_active=f.event_time
                ))
        except Exception as e:
            logger.error(f"GCP Discovery failed: {e}")
        return records

class FinOpsReasoner:
    def __init__(self, gcp_project: str, aws_region: str):
        vertexai.init(project=gcp_project, location="us-central1")
        self.gemini = GenerativeModel("gemini-3.1-pro")
        self.bedrock = boto3.client('bedrock-runtime', region_name=aws_region)

    def reason(self, anomalies: List[Dict]) -> List[Dict]:
        """Cross-cloud reasoning using Gemini 3.1 Pro (MEDIUM thinking) and Nova 2"""
        prompt = (
            f"Analyze these FinOps anomalies and identify 'Ghost' resources for decommissioning. "
            "Return JSON list: [{\"resource_id\": \"...\", \"reasoning\": \"...\", "
            "\"action\": \"delete|ignore\"}].\n"
            f"Anomalies: {json.dumps(anomalies)}"
        )

        # GCP Reasoning (Gemini 3.1 Pro)
        logger.info("Engaging Gemini 3.1 Pro for infrastructure reasoning...")
        resp = self.gemini.generate_content(
            prompt,
            generation_config={"thinking_level": "MEDIUM" if "3.1" in self.gemini.model_name else None}
        )
        return json.loads(re.search(r'\[.*\]', resp.text, re.DOTALL).group())

class TerraformRemediator:
    def remediate(self, action_plan: List[Dict], tf_dir: str):
        """Surgically comment out HCL blocks for identified waste"""
        for action in action_plan:
            if action['action'] == 'delete':
                res_id = action['resource_id']
                logger.info(f"Surgically decommissioning waste: {res_id}")
                for root, _, files in os.walk(tf_dir):
                    for file in files:
                        if file.endswith('.tf'):
                            path = os.path.join(root, file)
                            with open(path, 'r') as f:
                                content = f.read()
                            # Surgical regex: comment out the matching resource block
                            pattern = rf'(resource\s+"[^"]+"\s+"[^"]+"\s+{{[^}}]*name\s*=\s*"{res_id}"[^}}]*}})'
                            new_content = re.sub(
                                pattern,
                                lambda m: "\n".join([f"# {line}" for line in m.group(1).split("\n")]),
                                content,
                                flags=re.DOTALL
                            )
                            if new_content != content:
                                with open(path, 'w') as f:
                                    f.write(new_content)
                                logger.info(f"Resource {res_id} commented out in {path}")

class FinOpsOracle:
    def __init__(self, aws_cfg: Dict = None, gcp_cfg: Dict = None):
        self.aws_ingest = AWSIngestor(**aws_cfg) if aws_cfg else None
        self.gcp_ingest = GCPIngestor(**gcp_cfg) if gcp_cfg else None
        self.aws_disc = AWSDiscovery() if aws_cfg else None
        self.gcp_disc = GCPDiscovery(gcp_cfg['project_id']) if gcp_cfg else None
        self.reasoner = FinOpsReasoner(gcp_cfg['project_id'], "us-east-1") if gcp_cfg else None
        self.remediator = TerraformRemediator()
        self.records: List[CostRecord] = []
        self.inventory: List[DiscoveryRecord] = []

    def run_lifecycle(self, dry_run: bool = True):
        if self.aws_ingest:
            self.records.extend(self.aws_ingest.query_cur_v2("SELECT * FROM ..."))
        if self.gcp_ingest:
            self.records.extend(self.gcp_ingest.query_billing())
        if self.aws_disc:
            self.inventory.extend(self.aws_disc.discover_resources())
        if self.gcp_disc:
            self.inventory.extend(self.gcp_disc.discover_resources())

        # Identify anomalies (high cost, zero activity)
        anomalies = [
            {"resource_id": r.resource_id, "cost": r.net_unblended_cost}
            for r in self.records if r.net_unblended_cost > 100
        ]
        action_plan = self.reasoner.reason(anomalies)

        with open('remediation_plan_2026.json', 'w') as f:
            json.dump(action_plan, f, indent=2)
        if not dry_run:
            self.remediator.remediate(action_plan, ".")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["discover", "remediate"])
    parser.add_argument("--dry-run", action="store_true", default=True)
    args = parser.parse_args()
    # Scopes and configs would be loaded from .agent/settings.json
    oracle = FinOpsOracle(gcp_cfg={"project_id": "test-2026", "dataset_id": "billing", "table_id": "resource_usage"})
    oracle.run_lifecycle(dry_run=args.dry_run)
