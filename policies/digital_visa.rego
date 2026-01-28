package digital_visa

# Default deny
default allow = false

# Allow if all conditions are met
allow {
    intent_hash_matches
    visa_ttl_valid
    scope_constraints_met
}

# Rule: Validate intent_hash matches current_state_hash
intent_hash_matches {
    input.token.intent_hash == input.request.current_state_hash
}

# Rule: Validate visa_ttl is less than 60 seconds
visa_ttl_valid {
    input.token.visa_ttl < 60
}

# Rule: Scope-specific constraints
scope_constraints_met {
    # If scope is not billing, constraint is always met
    input.token.scope != "billing"
}

scope_constraints_met {
    # If scope is billing, check max_amount constraint
    input.token.scope == "billing"
    input.token.constraints.max_amount <= 150
}

# Violation messages for debugging
violations[msg] {
    not intent_hash_matches
    msg := "intent_hash does not match current_state_hash"
}

violations[msg] {
    not visa_ttl_valid
    msg := "visa_ttl must be less than 60 seconds"
}

violations[msg] {
    input.token.scope == "billing"
    not input.token.constraints.max_amount
    msg := "billing scope requires max_amount constraint"
}

violations[msg] {
    input.token.scope == "billing"
    input.token.constraints.max_amount > 150
    msg := sprintf("billing scope max_amount (%v) exceeds limit of 150", [input.token.constraints.max_amount])
}
