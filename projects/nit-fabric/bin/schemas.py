from typing import List, Optional
from pydantic import BaseModel, Field

class UnifiedSecurityRule(BaseModel):
    rule_id: str = Field(..., description="Unique identifier for the rule")
    platform: str = Field(..., description="AWS, GCP, or K8S")
    direction: str = Field(..., description="INGRESS or EGRESS")
    action: str = Field(..., description="ALLOW or DENY")
    protocol: str = Field("tcp", description="tcp, udp, icmp, etc.")
    port_range: Optional[str] = Field(None, description="e.g., '80, 443' or '1024-65535'")
    source_cidr: List[str] = Field(default_factory=list)
    destination_cidr: List[str] = Field(default_factory=list)
    is_legacy: bool = Field(False, description="Flagged for excision if true")

class BoundaryViolation(BaseModel):
    rule: UnifiedSecurityRule
    violation_type: str
    remediation_proposal: str
    advice: Optional[str] = ""
    severity: str = "CRITICAL"
    metadata: dict = Field(default_factory=dict, description="Contextual info for remediation")
