package digital_visa

# Test: Valid token with all conditions met
test_allow_valid_token {
    allow with input as {
        "token": {
            "intent_hash": "abc123",
            "visa_ttl": 30,
            "scope": "read"
        },
        "request": {
            "current_state_hash": "abc123"
        }
    }
}

# Test: Valid billing token with max_amount constraint
test_allow_valid_billing_token {
    allow with input as {
        "token": {
            "intent_hash": "xyz789",
            "visa_ttl": 45,
            "scope": "billing",
            "constraints": {
                "max_amount": 100
            }
        },
        "request": {
            "current_state_hash": "xyz789"
        }
    }
}

# Test: Deny when intent_hash does not match
test_deny_mismatched_intent_hash {
    not allow with input as {
        "token": {
            "intent_hash": "abc123",
            "visa_ttl": 30,
            "scope": "read"
        },
        "request": {
            "current_state_hash": "different"
        }
    }
}

# Test: Deny when visa_ttl exceeds 60 seconds
test_deny_expired_visa_ttl {
    not allow with input as {
        "token": {
            "intent_hash": "abc123",
            "visa_ttl": 65,
            "scope": "read"
        },
        "request": {
            "current_state_hash": "abc123"
        }
    }
}

# Test: Deny billing token with max_amount exceeding 150
test_deny_billing_exceeds_limit {
    not allow with input as {
        "token": {
            "intent_hash": "xyz789",
            "visa_ttl": 30,
            "scope": "billing",
            "constraints": {
                "max_amount": 200
            }
        },
        "request": {
            "current_state_hash": "xyz789"
        }
    }
}

# Test: Deny billing token without max_amount constraint
test_deny_billing_missing_constraint {
    not allow with input as {
        "token": {
            "intent_hash": "xyz789",
            "visa_ttl": 30,
            "scope": "billing",
            "constraints": {}
        },
        "request": {
            "current_state_hash": "xyz789"
        }
    }
}

# Test: Allow billing token with max_amount exactly 150
test_allow_billing_at_limit {
    allow with input as {
        "token": {
            "intent_hash": "xyz789",
            "visa_ttl": 30,
            "scope": "billing",
            "constraints": {
                "max_amount": 150
            }
        },
        "request": {
            "current_state_hash": "xyz789"
        }
    }
}

# Test: Violations message for mismatched hash
test_violations_mismatched_hash {
    violations["intent_hash does not match current_state_hash"] with input as {
        "token": {
            "intent_hash": "abc123",
            "visa_ttl": 30,
            "scope": "read"
        },
        "request": {
            "current_state_hash": "different"
        }
    }
}

# Test: Violations message for expired TTL
test_violations_expired_ttl {
    violations["visa_ttl must be less than 60 seconds"] with input as {
        "token": {
            "intent_hash": "abc123",
            "visa_ttl": 65,
            "scope": "read"
        },
        "request": {
            "current_state_hash": "abc123"
        }
    }
}
