# Tech Stack: nit-fabric

## Core Engine
- **Runtime**: Python 3.10+
- **Schema Validation**: Pydantic v2
- **Cloud SDK (AWS)**: Boto3
- **Cloud SDK (GCP)**: google-cloud-compute
- **HCL Parser**: hcl2

## Infrastructure
- **Orchestrator**: Terraform 1.5+
- **Providers**: `hashicorp/aws`, `hashicorp/google`
- **State Management**: S3/GCS with state-file isolation.

## Security & Verification
- **Encryption**: IKEv2 / AES-256 / SHA-256
- **Routing**: BGP with BFD (300ms)
- **Visualization**: Mermaid.js