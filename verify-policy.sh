#!/bin/bash

# Manual OPA Policy Verification Script
# Tests the digital_visa.rego policy with example inputs

echo "═══════════════════════════════════════════════════════════"
echo "   Digital Visa OPA Policy - Manual Verification"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Display policy content
echo "📄 POLICY RULES:"
echo "  1. intent_hash must match current_state_hash"
echo "  2. visa_ttl must be < 60 seconds"
echo "  3. For billing scope: max_amount must be <= 150"
echo ""

# Display test case 1 - Valid
echo "═══════════════════════════════════════════════════════════"
echo "TEST CASE 1: Valid Input (should allow)"
echo "═══════════════════════════════════════════════════════════"
cat examples/opa_input_valid.json | jq '.'
echo ""
echo "Expected: ALLOW ✓"
echo ""

# Display test case 2 - Invalid
echo "═══════════════════════════════════════════════════════════"
echo "TEST CASE 2: Invalid Input (should deny)"
echo "═══════════════════════════════════════════════════════════"
cat examples/opa_input_invalid.json | jq '.'
echo ""
echo "Expected: DENY ✗"
echo "Violations:"
echo "  - intent_hash mismatch (abc123 != different_hash)"
echo "  - visa_ttl too high (75 >= 60)"
echo "  - max_amount exceeds limit (200 > 150)"
echo ""

# Check if OPA is available
if command -v opa &> /dev/null; then
    echo "═══════════════════════════════════════════════════════════"
    echo "   Running OPA Evaluation"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    echo "Test 1 - Valid Input:"
    opa eval -d policies/digital_visa.rego -i examples/opa_input_valid.json "data.digital_visa.allow" --format pretty
    echo ""
    
    echo "Test 2 - Invalid Input:"
    opa eval -d policies/digital_visa.rego -i examples/opa_input_invalid.json "data.digital_visa.allow" --format pretty
    echo ""
    
    echo "Test 2 - Violations:"
    opa eval -d policies/digital_visa.rego -i examples/opa_input_invalid.json "data.digital_visa.violations" --format pretty
    echo ""
else
    echo "⚠️  OPA not installed. Install from: https://www.openpolicyagent.org"
    echo ""
    echo "To manually verify, run:"
    echo "  opa eval -d policies/digital_visa.rego -i examples/opa_input_valid.json \"data.digital_visa.allow\""
fi

echo "═══════════════════════════════════════════════════════════"
