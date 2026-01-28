# Technical Specification: Digital Visa Protocol

## Version: 1.0.0
## Date: 2026-01-28

## 1. Protocol Specification

### 1.1 Digital Visa Request Format

**Endpoint**: `POST /api/v1/digital-visa/request`

**Request Schema**:
```json
{
  "agent_id": "string (DID format: did:agent:7742)",
  "task_hash": "string (SHA-256 hex)",
  "scopes": ["string"],
  "parent_token": "string (JWT)",
  "reasoning_trace": {
    "chain_of_thought": ["string"],
    "intent": "string",
    "context": {}
  },
  "metadata": {
    "model": "string",
    "version": "string",
    "timestamp": "ISO8601"
  }
}
```

**Response Schema**:
```json
{
  "visa_token": "string (A-JWT)",
  "transaction_id": "string (UUID)",
  "expires_at": "ISO8601",
  "constraints": {},
  "consensus_required": "boolean"
}
```

### 1.2 Agentic-JWT (A-JWT) Token Structure

**Header**:
```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "digital-visa-key-2026-01"
}
```

**Payload**:
```json
{
  "sub": "did:agent:7742",
  "iss": "digital-visa-idp",
  "aud": ["billing-service", "crm-service"],
  "exp": 1735405260,
  "iat": 1735405200,
  "nbf": 1735405200,
  "jti": "550e8400-e29b-41d4-a716-446655440000",
  "intent_hash": "a3f2b1c4d5e6f7g8h9i0j1k2l3m4n5o6",
  "scope": ["billing:write", "crm:read"],
  "visa_ttl": "60s",
  "constraints": {
    "max_amount": 150,
    "currency": "USD",
    "approver": "user_id_99",
    "allowed_operations": ["refund"],
    "rate_limit": "5/minute"
  },
  "parent_delegation": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "consensus_proof": {
    "required": false,
    "threshold": "2/3",
    "participants": []
  }
}
```

### 1.3 Policy Decision Point (PDP) Interface

**OPA/Rego Policy Structure**:

```rego
package digital_visa.policies

import future.keywords.if
import future.keywords.in

# Default deny
default allow = false

# Allow low-value refunds without approval
allow if {
    input.action == "refund"
    input.amount <= 100
    input.agent_reputation >= 0.8
}

# Require supervisor approval for high-value refunds
allow if {
    input.action == "refund"
    input.amount > 100
    input.amount <= 1000
    input.supervisor_approved == true
}

# Require Byzantine consensus for critical operations
allow if {
    input.action in ["wire_transfer", "account_closure"]
    input.consensus_achieved == true
    input.consensus_ratio >= 0.67
}

# Reasoning trace validation
reasoning_valid if {
    count(input.reasoning_trace.chain_of_thought) >= 3
    input.reasoning_trace.intent != ""
    valid_hash(input.task_hash, input.reasoning_trace)
}

# Helper function to validate hash
valid_hash(hash, trace) if {
    computed := crypto.sha256(json.marshal(trace))
    computed == hash
}
```

### 1.4 Service Mesh Integration (Envoy Filter)

**Envoy External Authorization Filter Configuration**:

```yaml
http_filters:
  - name: envoy.filters.http.ext_authz
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.filters.http.ext_authz.v3.HttpService
      http_service:
        server_uri:
          uri: http://digital-visa-pep:8080
          cluster: digital_visa_pep_cluster
          timeout: 0.250s
        authorization_request:
          allowed_headers:
            patterns:
              - exact: authorization
              - exact: x-agent-id
              - exact: x-intent-hash
              - exact: x-transaction-id
        authorization_response:
          allowed_upstream_headers:
            patterns:
              - exact: x-visa-validated
              - exact: x-reasoning-trace-id
```

## 2. Implementation Specifications

### 2.1 Agent Registry (DID-based)

**DID Format**: `did:agent:{unique_id}`

**Registry Entry Schema**:
```json
{
  "did": "did:agent:7742",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...",
  "model": "gpt-4",
  "version": "2026.01",
  "created_at": "2026-01-15T10:00:00Z",
  "reputation_score": 0.95,
  "total_operations": 15000,
  "successful_operations": 14850,
  "failed_operations": 150,
  "consensus_participation": 500,
  "last_active": "2026-01-28T16:59:00Z",
  "capabilities": ["billing", "crm", "support"],
  "risk_profile": "low",
  "metadata": {
    "organization": "acme-corp",
    "department": "customer-service",
    "supervisor": "user_id_99"
  }
}
```

**API Endpoints**:
- `POST /api/v1/agents/register` - Register new agent
- `GET /api/v1/agents/{did}` - Get agent details
- `PUT /api/v1/agents/{did}/reputation` - Update reputation score
- `DELETE /api/v1/agents/{did}` - Deactivate agent

### 2.2 Byzantine Jury Consensus Engine

**Consensus Request Schema**:
```json
{
  "operation_id": "op_550e84",
  "operation_type": "wire_transfer",
  "operation_details": {
    "amount": 50000,
    "currency": "USD",
    "destination": "account_789"
  },
  "required_consensus": 2,
  "total_agents": 3,
  "timeout": "30s",
  "agents": [
    "did:agent:7742",
    "did:agent:8843",
    "did:agent:9944"
  ]
}
```

**Consensus Response Schema**:
```json
{
  "operation_id": "op_550e84",
  "consensus_achieved": true,
  "agreements": 3,
  "disagreements": 0,
  "abstentions": 0,
  "consensus_ratio": 1.0,
  "agent_responses": [
    {
      "agent_id": "did:agent:7742",
      "decision": "approve",
      "reasoning_hash": "abc123...",
      "signature": "sig_xyz..."
    },
    {
      "agent_id": "did:agent:8843",
      "decision": "approve",
      "reasoning_hash": "def456...",
      "signature": "sig_uvw..."
    },
    {
      "agent_id": "did:agent:9944",
      "decision": "approve",
      "reasoning_hash": "ghi789...",
      "signature": "sig_rst..."
    }
  ],
  "executed_at": "2026-01-28T17:00:00Z"
}
```

**Consensus Algorithm**:
1. Distribute operation request to N independent agents
2. Each agent analyzes and generates reasoning chain
3. Each agent requests Digital Visa independently
4. Collect M responses (with timeout)
5. Validate that M/N >= threshold (typically 2/3)
6. Verify reasoning hash diversity (prevent collusion)
7. Issue collective visa if consensus achieved

### 2.3 Reasoning Trace Storage

**Trace Entry Schema**:
```json
{
  "trace_id": "trace_550e84",
  "agent_id": "did:agent:7742",
  "operation_id": "op_550e84",
  "timestamp": "2026-01-28T16:59:14.045Z",
  "reasoning_chain": [
    {
      "step": 1,
      "timestamp": "2026-01-28T16:59:14.100Z",
      "thought": "string",
      "action": "string",
      "observation": "string",
      "tool_calls": [],
      "latency_ms": 150
    }
  ],
  "final_intent": "string",
  "intent_hash": "sha256_hex",
  "visa_issued": "visa_id",
  "visa_constraints": {},
  "execution_result": {
    "status": "success",
    "output": {},
    "errors": []
  },
  "performance_metrics": {
    "total_latency_ms": 850,
    "token_count": 1250,
    "api_calls": 3
  },
  "vector_embedding": [0.123, 0.456, ...],
  "attention_weights": {},
  "model_metadata": {
    "model": "gpt-4",
    "temperature": 0.7,
    "version": "2026.01"
  }
}
```

**Storage Backend Options**:
- **Primary**: PostgreSQL with pgvector extension
- **Vector Search**: Pinecone, Weaviate, or Qdrant
- **Immutability**: Optional blockchain anchoring (Hyperledger Fabric)

### 2.4 Policy Decision Point (PDP) Implementation

**PDP Service Specification**:

**Endpoints**:
- `POST /api/v1/pdp/evaluate` - Evaluate policy decision
- `GET /api/v1/pdp/policies` - List active policies
- `POST /api/v1/pdp/policies` - Create/update policy
- `GET /api/v1/pdp/health` - Health check

**Evaluation Request**:
```json
{
  "input": {
    "agent_id": "did:agent:7742",
    "action": "refund",
    "resource": "customer_123",
    "amount": 125.00,
    "currency": "USD",
    "reasoning_trace": {...},
    "task_hash": "abc123...",
    "parent_token": "eyJ...",
    "context": {
      "time_of_day": "business_hours",
      "agent_reputation": 0.95,
      "supervisor_available": true
    }
  }
}
```

**Evaluation Response**:
```json
{
  "decision": "allow",
  "visa_token": "eyJ...",
  "constraints": {
    "max_amount": 150,
    "expires_in": 60
  },
  "requires_approval": false,
  "requires_consensus": false,
  "policy_version": "1.0.0",
  "evaluated_at": "2026-01-28T16:59:14.045Z"
}
```

### 2.5 Policy Enforcement Point (PEP) Implementation

**PEP Service Specification**:

**Endpoints**:
- `POST /api/v1/pep/verify` - Verify A-JWT token
- `POST /api/v1/pep/validate-consensus` - Validate consensus proof
- `GET /api/v1/pep/health` - Health check

**Verification Request**:
```json
{
  "token": "eyJ...",
  "request": {
    "method": "POST",
    "path": "/api/billing/refund",
    "body": {...},
    "headers": {...}
  },
  "current_reasoning_hash": "abc123..."
}
```

**Verification Response**:
```json
{
  "valid": true,
  "agent_id": "did:agent:7742",
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "constraints_met": true,
  "reasoning_hash_valid": true,
  "not_expired": true,
  "not_replayed": true,
  "audience_match": true,
  "trace_id": "trace_550e84"
}
```

## 3. Security Specifications

### 3.1 Cryptographic Standards

- **Signature Algorithm**: RS256 (RSA with SHA-256) or ES256 (ECDSA with SHA-256)
- **Key Length**: Minimum 2048 bits for RSA, 256 bits for ECDSA
- **Hash Function**: SHA-256 for all integrity checks
- **Transport Security**: TLS 1.3 with mutual authentication (mTLS)
- **Token Encryption**: Optional JWE for sensitive constraints

### 3.2 Key Management

- **IDP Signing Keys**: Stored in HSM (Hardware Security Module)
- **Key Rotation**: Automatic rotation every 90 days
- **Key Distribution**: JWKS (JSON Web Key Set) endpoint
- **Backup**: Multi-region key replication with encryption at rest

### 3.3 Rate Limiting

- **Visa Requests**: 100 requests/minute per agent
- **Policy Evaluation**: 500 requests/minute per PDP instance
- **Token Verification**: 1000 requests/minute per PEP instance

### 3.4 Audit Logging

All operations must be logged with:
- Timestamp (ISO8601)
- Agent ID
- Operation type
- Decision outcome
- Policy version
- Reasoning trace ID
- Execution result

## 4. Monitoring & Observability

### 4.1 Metrics

**Key Performance Indicators**:
- `digital_visa_request_latency_ms` (histogram)
- `digital_visa_approval_rate` (gauge)
- `digital_visa_consensus_success_rate` (gauge)
- `agent_reputation_score` (gauge)
- `policy_evaluation_errors` (counter)
- `token_verification_failures` (counter)

**SLOs (Service Level Objectives)**:
- 95th percentile visa request latency < 100ms
- 99.9% visa approval API availability
- 99.5% token verification success rate

### 4.2 Distributed Tracing

- **Standard**: OpenTelemetry
- **Trace Context**: Propagated via W3C Trace Context headers
- **Spans**: All components instrumented with detailed spans

### 4.3 Alerting

**Critical Alerts**:
- Visa approval rate drops below 90%
- Consensus failures exceed 5% threshold
- Token verification latency exceeds 50ms
- Agent reputation scores drop suddenly
- Policy evaluation errors spike

## 5. Deployment Specifications

### 5.1 Infrastructure Requirements

**Minimum Resources**:
- **PDP**: 2 vCPU, 4GB RAM, auto-scaling 2-10 instances
- **PEP**: 4 vCPU, 8GB RAM, auto-scaling 3-15 instances
- **Agent Registry**: 2 vCPU, 8GB RAM, 2 instances (active-passive)
- **Reasoning Trace DB**: PostgreSQL 14+, 8 vCPU, 32GB RAM
- **Vector Database**: Dedicated cluster for semantic search

### 5.2 High Availability

- Multi-region deployment (minimum 2 regions)
- Active-active configuration for stateless services
- Database replication with automatic failover
- Load balancing with health checks

### 5.3 Disaster Recovery

- **RPO** (Recovery Point Objective): 5 minutes
- **RTO** (Recovery Time Objective): 15 minutes
- Automated backups every 6 hours
- Cross-region backup replication
- Regular disaster recovery drills

## 6. API Versioning

- **Current Version**: v1
- **Version Format**: `/api/v{major}/...`
- **Deprecation Policy**: 6 months notice for breaking changes
- **Backward Compatibility**: Maintained within major version
