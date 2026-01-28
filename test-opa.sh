#!/bin/bash

# OPA Policy Testing Script
# This script tests the digital_visa.rego policy

set -e

echo "╔═══════════════════════════════════════════════════════╗"
echo "║     Digital Visa OPA Policy Test Runner             ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Check if OPA is installed
if ! command -v opa &> /dev/null; then
    echo "⚠️  OPA is not installed."
    echo ""
    echo "To test the OPA policy, install OPA:"
    echo "  Linux: curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64_static"
    echo "  macOS: brew install opa"
    echo "  Or visit: https://www.openpolicyagent.org/docs/latest/#running-opa"
    echo ""
    echo "Then run: opa test policies/"
    echo ""
    exit 0
fi

echo "✅ OPA found: $(opa version)"
echo ""

# Run OPA tests
echo "Running OPA tests..."
echo ""

opa test policies/ -v

echo ""
echo "✅ All OPA tests passed!"
