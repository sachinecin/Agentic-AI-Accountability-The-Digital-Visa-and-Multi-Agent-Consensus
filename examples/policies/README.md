# Digital Visa Protocol Policies (OPA/Rego)

This directory contains Open Policy Agent (OPA) Rego policies for the Digital Visa Protocol.

## Policy Files

- `refund_policy.rego` - Refund authorization policies
- `critical_operations.rego` - High-stakes operation policies
- `rate_limiting.rego` - Rate limiting policies
- `reputation_based.rego` - Reputation-based authorization

## Running Policies

### Install OPA

```bash
# macOS
brew install opa

# Linux
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
chmod +x opa

# Windows
# Download from https://www.openpolicyagent.org/docs/latest/#running-opa
```

### Test a Policy

```bash
# Evaluate policy with input
opa eval -d refund_policy.rego -i test_input.json "data.digital_visa.refund.allow"

# Run OPA server
opa run --server refund_policy.rego

# Test via HTTP
curl -X POST http://localhost:8181/v1/data/digital_visa/refund/allow \
  -H 'Content-Type: application/json' \
  -d @test_input.json
```

## Policy Structure

All policies follow the Digital Visa Protocol conventions:

1. **Package**: `digital_visa.{domain}`
2. **Decision**: `allow` or `deny`
3. **Input**: Agent request with reasoning trace
4. **Output**: Boolean decision + optional constraints

## Example Input

```json
{
  "agent_id": "did:agent:7742",
  "agent_reputation": 0.95,
  "action": "refund",
  "amount": 125.00,
  "currency": "USD",
  "reasoning_trace": {
    "chain_of_thought": [
      "Analyzed customer complaint",
      "Verified order history",
      "Calculated refund amount"
    ],
    "intent": "Process refund for Customer #123"
  },
  "task_hash": "a3f2b1c4d5e6f7g8h9i0j1k2l3m4n5o6",
  "context": {
    "time_of_day": "business_hours",
    "supervisor_available": true
  }
}
```
