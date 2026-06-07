# Executive Implementation Plan: Vault Auth Modernization

**Status**: [CERTIFIED] | **Design Authority**: @swarm-architect

## 1. The Strategy: Implement a Strategy-pattern based authentication abstraction for Vault to support multi-cloud (AWS/GCP) and simplify credential management via standardized variables.

## 2. Architecture Trade-Off Matrix

| Architectural Path | Chosen? | Trade-Off Accepted | Mitigation Strategy |
|---|---|---|---|
| **Strategy Pattern Abstraction** | **Yes** | Increased initial boilerplate for each auth method. | Use a common base class for shared validation logic. |
| **Unified Environment Variables** | **Yes** | Breaking change for existing pipelines. | Update all repository documentation and tests immediately. |
| **Monolithic `if/else` block** | **No** | Violates OCP; becomes unmaintainable as cloud providers grow. | N/A |

## 3. Manufacturing Blueprint (TDD-First)

### Phase 1: Success Characterization (Tests)
- [x] **Step 1.1**: Mock existing auth methods in a new test suite.
  - **Action**: `pytest projects/vault/tests/test_auth_strategies.py`
  - **Success**: Verify that each strategy can correctly build its API payload.

### Phase 2: Surgical Implementation (Engineering)
- [x] **Step 2.1**: Refactor `LocalVaultClient` to use an `AuthStrategy` factory.
  - **Focus**: `projects/vault/lib/vault_client.py`
  - **Protocol**: `strict-patch`.
- [x] **Step 2.2**: Implement `AWSAuthStrategy` and `GCPAuthStrategy`.
  - **Focus**: `projects/vault/lib/auth/`
- [x] **Step 2.3**: Implement `UnifiedConfigStrategy` to handle `VAULT_AUTH_*` environment variables.

### Phase 3: Blast Radius Verification (Audit Prep)
- [x] **Step 3.1**: Verify AWS/GCP login flows with mocks.
- [x] **Step 3.2**: 100% test coverage for the new auth layer.

## 4. Production Readiness & Day-Two Operations
- **Observability**: Log authentication type used and success/failure rates.
- **Security**: Never log `VAULT_AUTH_SECRET` contents. Ensure `boto3` and `google-auth` dependencies are pinned.
- **Resilience**: Implement retries for cloud metadata server calls (AWS/GCP).

## 5. Financial Guardrails (Cost Gating)
- **Token Efficiency**: N/A (Client-side logic).
- **Infrastructure Opex**: Minimal impact; local libraries only.
