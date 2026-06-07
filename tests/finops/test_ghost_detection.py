from unittest.mock import patch

import pytest

# Mocking the yet-to-be-implemented FinOpsOracle
# In a real TDD flow, we'd import the class and it would fail to import.
# For this task, I'll assume the logic will be in bin/finops_oracle.py

class TestGhostDetection:

    @pytest.fixture
    def mock_aws_cur_v2(self):
        """Synthetic AWS CUR v2 data (Parquet/Iceberg style)"""
        return [
            {
                "line_item_resource_id": "vol-0123456789abcdef0",
                "line_item_usage_type": "EBS:VolumeUsage.gp3",
                "line_item_usage_amount": 100.0,
                "line_item_currency_code": "USD",
                "bill_billing_period_start_date": "2026-01-01T00:00:00Z"
            },
            {
                "line_item_resource_id": (
                    "arn:aws:elasticloadbalancing:us-east-1:123456789012:"
                    "loadbalancer/app/ghost-lb/50dc6c495c0c9188"
                ),
                "line_item_usage_type": "LoadBalancerUsage",
                "line_item_usage_amount": 24.0,
                "line_item_currency_code": "USD",
                "bill_billing_period_start_date": "2026-01-01T00:00:00Z"
            }
        ]

    @pytest.fixture
    def mock_gcp_billing(self):
        """Synthetic GCP BigQuery Billing data"""
        return [
            {
                "resource": {"name": "projects/my-project/zones/us-central1-a/disks/ghost-disk"},
                "usage": {"amount": 50.0, "unit": "byte-seconds"},
                "cost": 0.50,
                "currency": "USD",
                "usage_start_time": "2026-01-01T00:00:00Z"
            }
        ]

    @patch("bin.finops_oracle.AWSDiscovery")
    @patch("bin.finops_oracle.GCPDiscovery")
    def test_detect_unattached_ebs(self, mock_gcp, mock_aws, mock_aws_cur_v2):
        """Test detection of unattached EBS volumes using Resource Explorer V2 attributes"""
        from bin.finops_oracle import FinOpsOracle

        # Setup AWS Mock
        mock_aws_instance = mock_aws.return_value
        mock_aws_instance.get_cur_v2_data.return_value = mock_aws_cur_v2
        mock_aws_instance.get_resource_explorer_v2_status.return_value = {
            "vol-0123456789abcdef0": {
                "status": "available", # 'available' means not attached
                "last_accessed_via_agentless_scan": "2025-12-20T10:00:00Z" # Old scan
            }
        }

        oracle = FinOpsOracle()
        ghosts = oracle.detect_ghosts(provider="aws")

        ebs_ghosts = [g for g in ghosts if g["id"] == "vol-0123456789abcdef0"]
        assert len(ebs_ghosts) == 1
        assert ebs_ghosts[0]["signature_id"] == "AWS-EBS-001"
        assert ebs_ghosts[0]["risk_level"] == "LOW"

    @patch("bin.finops_oracle.AWSDiscovery")
    def test_detect_idle_lb(self, mock_aws, mock_aws_cur_v2):
        """Test detection of idle Load Balancers using CloudWatch + Network Explorer V2"""
        from bin.finops_oracle import FinOpsOracle

        mock_aws_instance = mock_aws.return_value
        mock_aws_instance.get_cur_v2_data.return_value = mock_aws_cur_v2
        lb_arn = "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/ghost-lb/50dc6c495c0c9188"

        mock_aws_instance.get_metric_data.return_value = {
            lb_arn: {
                "ActiveConnectionCount": 0,
                "RequestCount": 0
            }
        }
        mock_aws_instance.get_network_explorer_v2_status.return_value = {
            lb_arn: {"network_explorer_v2_flow_logs_active": False}
        }

        oracle = FinOpsOracle()
        ghosts = oracle.detect_ghosts(provider="aws")

        lb_ghosts = [g for g in ghosts if g["id"] == lb_arn]
        assert len(lb_ghosts) == 1
        assert lb_ghosts[0]["signature_id"] == "AWS-ELB-002"

    @patch("bin.finops_oracle.GCPDiscovery")
    def test_detect_orphaned_gcp_disk(self, mock_gcp, mock_gcp_billing):
        """Test detection of orphaned GCP disks using SCC Agentless Scan attributes"""
        from bin.finops_oracle import FinOpsOracle

        mock_gcp_instance = mock_gcp.return_value
        mock_gcp_instance.get_bq_billing_data.return_value = mock_gcp_billing
        disk_id = "projects/my-project/zones/us-central1-a/disks/ghost-disk"

        mock_gcp_instance.get_scc_agentless_scan_status.return_value = {
            disk_id: {
                "status": "INACTIVE",
                "last_seen": "2025-11-15T00:00:00Z"
            }
        }

        oracle = FinOpsOracle()
        ghosts = oracle.detect_ghosts(provider="gcp")

        disk_ghosts = [g for g in ghosts if g["id"] == disk_id]
        assert len(disk_ghosts) == 1
        assert disk_ghosts[0]["signature_id"] == "GCP-GCE-001"
