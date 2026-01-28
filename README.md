# Agentic AI Accountability: The Digital Visa Protocol

The transition from Generative AI to Agentic AI has shifted the leadership mandate from managing "output quality" to governing "actionable intent." In 2026, enterprise-grade accountability is no longer a post-mortem audit process; it is a real-time architectural requirement embedded into the agent's execution stack.

## Digital Visa Protocol Implementation

This repository implements the **Digital Visa Protocol**, a secure framework for validating AI agent actions through:

- **OPA Rego Policy**: Validates transaction-bound A-JWTs (Agentic JWTs) with strict rules
- **TypeScript/Node.js Helper**: Mints secure A-JWTs with SHA-256 intent hashes and short-lived nonces

### Quick Start

```bash
# Install dependencies
npm install

# Build the project
npm run build

# Run tests
npm test

# Run OPA policy tests (requires OPA installed)
./test-opa.sh

# Run examples
npx ts-node examples/usage.ts
```

### Key Features

1. **Intent Hash Validation**: Every token is bound to a specific transaction via SHA-256 hash
2. **Time-to-Live (TTL) Constraints**: Tokens expire in under 60 seconds
3. **Scope-Based Constraints**: Billing operations limited to amounts ≤ 150
4. **Nonce-Based Replay Protection**: Each token includes a unique nonce
5. **Comprehensive Testing**: 19 TypeScript tests + OPA policy tests

### Documentation

See [DIGITAL_VISA.md](./DIGITAL_VISA.md) for complete documentation, API reference, and usage examples.

### Project Structure

```
.
├── policies/               # OPA Rego policies and tests
│   ├── digital_visa.rego
│   └── digital_visa_test.rego
├── src/                   # TypeScript source code
│   ├── digitalVisa.ts    # Main implementation
│   ├── digitalVisa.test.ts
│   └── index.ts
├── examples/              # Usage examples and test data
│   ├── usage.ts
│   ├── opa_input_valid.json
│   └── opa_input_invalid.json
└── dist/                  # Compiled JavaScript (generated)
```
