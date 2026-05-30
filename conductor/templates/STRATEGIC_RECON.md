# Strategic Reconnaissance Report: [Track Name]

**Status**: [DRAFT | REVIEW-READY] | **Investigator**: @swarm-scout

## 1. Architectural Topology (The Mental Map)
[Provide a Mermaid.js diagram or a high-signal description of the current system state and how the proposed change intersects with existing components.]

## 2. Blast Radius Analysis
[Identify every file, module, and infrastructure resource affected by this change.]
- **Primary Impact**: [Files directly modified]
- **Secondary Impact**: [Dependent files/services that may require regression testing]
- **Infrastructure Impact**: [Cloud resources, IAM roles, or security groups affected]

## 3. Systemic Risk Discovery
[Identify "Ghost Dependencies", hidden coupling, or potential architectural pitfalls.]
- **Risk 1**: [Description + Impact]
- **Risk 2**: [Description + Impact]

## 4. Operational Constraints & SLOs
[Define the performance, security, and cost boundaries for this track.]
- **Concurrency**: [e.g., Must sustain >10k RPS]
- **Latency**: [e.g., p99 <100ms]
- **Cost**: [e.g., Zero increase in Opex]

## 5. Ground Truth Verification
[Empirical evidence gathered during discovery.]
- **Grep/AST Results**: [Summary of key findings]
- **Memory Recall**: [Relevant insights from @memory-agent]
