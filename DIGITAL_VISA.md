# Digital Visa Protocol

A comprehensive implementation of the Digital Visa protocol with OPA (Open Policy Agent) Rego policy validation and Node.js/TypeScript helpers for minting transaction-bound A-JWTs (Agentic JWTs).

## Overview

The Digital Visa protocol provides a secure way to validate AI agent actions through:

1. **OPA Rego Policy**: Validates A-JWT tokens against strict rules
2. **TypeScript Helper**: Mints transaction-bound JWTs with SHA-256 intent hashes and short-lived nonces

## Components

### 1. OPA Rego Policy (`policies/digital_visa.rego`)

The policy validates A-JWT tokens with the following rules:

- **Intent Hash Validation**: `input.token.intent_hash` must match `input.request.current_state_hash`
- **TTL Validation**: `input.token.visa_ttl` must be less than 60 seconds
- **Billing Constraints**: For scope "billing", `input.token.constraints.max_amount` must be ≤ 150

#### Policy Usage

```bash
# Test the policy
opa test policies/

# Evaluate the policy
opa eval -d policies/digital_visa.rego -i input.json "data.digital_visa.allow"
```

#### Example Input

```json
{
  "token": {
    "intent_hash": "abc123...",
    "visa_ttl": 30,
    "scope": "billing",
    "constraints": {
      "max_amount": 100
    }
  },
  "request": {
    "current_state_hash": "abc123..."
  }
}
```

### 2. TypeScript A-JWT Helper (`src/digitalVisa.ts`)

Provides functions to mint, decode, and verify A-JWTs.

#### Installation

```bash
npm install
```

#### API Reference

##### `generateIntentHash(data: TransactionData): string`

Generates a SHA-256 hash from transaction data.

```typescript
const hash = generateIntentHash({
  action: 'transfer',
  scope: 'billing',
  timestamp: Date.now(),
  parameters: { amount: 100 }
});
```

##### `generateNonce(): string`

Generates a short-lived nonce using random bytes and timestamp.

```typescript
const nonce = generateNonce();
```

##### `mintAJWT(options: MintOptions): string`

Mints a transaction-bound A-JWT.

```typescript
const token = mintAJWT({
  scope: 'billing',
  visa_ttl: 30, // seconds
  constraints: {
    max_amount: 150
  },
  transactionData: {
    action: 'charge',
    scope: 'billing',
    timestamp: Date.now(),
    parameters: { amount: 100 }
  },
  secret: 'your-secret-key'
});
```

##### `decodeAJWT(token: string): AJWTPayload | null`

Decodes an A-JWT without verification (for inspection).

```typescript
const payload = decodeAJWT(token);
console.log(payload.intent_hash);
```

##### `verifyAJWT(token: string, secret: string): AJWTPayload`

Verifies and decodes an A-JWT.

```typescript
try {
  const verified = verifyAJWT(token, secret);
  console.log('Token valid:', verified);
} catch (error) {
  console.error('Token invalid:', error);
}
```

## Complete Example

```typescript
import { mintAJWT, generateIntentHash } from './src/digitalVisa';

// Define transaction
const transactionData = {
  action: 'charge',
  scope: 'billing',
  timestamp: Date.now(),
  parameters: {
    userId: 'user123',
    amount: 100,
    currency: 'USD'
  }
};

// Mint A-JWT
const token = mintAJWT({
  scope: 'billing',
  visa_ttl: 30, // 30 seconds
  constraints: {
    max_amount: 150
  },
  transactionData,
  secret: process.env.JWT_SECRET || 'your-secret-key'
});

console.log('Minted A-JWT:', token);

// Prepare OPA input
const currentStateHash = generateIntentHash(transactionData);

const opaInput = {
  token: {
    intent_hash: /* decoded from token */,
    visa_ttl: 30,
    scope: 'billing',
    constraints: {
      max_amount: 150
    }
  },
  request: {
    current_state_hash: currentStateHash
  }
};

// Validate with OPA policy
// opa eval -d policies/digital_visa.rego -i opa_input.json "data.digital_visa.allow"
```

## Testing

### OPA Policy Tests

```bash
npm run test:opa
```

### TypeScript Tests

```bash
npm test
```

### Build

```bash
npm run build
```

## A-JWT Payload Structure

```typescript
interface AJWTPayload {
  intent_hash: string;      // SHA-256 hash of transaction data
  visa_ttl: number;         // Time-to-live in seconds
  scope: string;            // Scope of the action (e.g., 'billing', 'read')
  nonce: string;            // Short-lived nonce for uniqueness
  constraints?: {           // Optional constraints
    max_amount?: number;
    [key: string]: any;
  };
  iat: number;             // Issued at (Unix timestamp)
  exp: number;             // Expiration time (Unix timestamp)
}
```

## Security Considerations

1. **Short-lived tokens**: Default TTL is 30 seconds, maximum 60 seconds
2. **Intent binding**: Each token is bound to a specific transaction via intent_hash
3. **Nonce uniqueness**: Each token includes a unique nonce to prevent replay attacks
4. **Scope constraints**: Billing operations are limited to max_amount ≤ 150
5. **Secret management**: Store JWT secrets securely (use environment variables)

## License

MIT
