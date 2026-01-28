package digital_visa.refund

import future.keywords.if
import future.keywords.in

# Default deny all refunds
default allow = false

# Allow low-value refunds for high-reputation agents
allow if {
    input.action == "refund"
    input.amount <= 100
    input.agent_reputation >= 0.8
    valid_reasoning
}

# Allow medium-value refunds with supervisor approval
allow if {
    input.action == "refund"
    input.amount > 100
    input.amount <= 1000
    input.supervisor_approved == true
    input.agent_reputation >= 0.7
    valid_reasoning
}

# Allow high-value refunds with consensus
allow if {
    input.action == "refund"
    input.amount > 1000
    input.consensus_achieved == true
    input.consensus_ratio >= 0.67
    valid_reasoning
}

# Validate reasoning trace
valid_reasoning if {
    count(input.reasoning_trace.chain_of_thought) >= 3
    input.reasoning_trace.intent != ""
}

# Generate constraints for approved refunds
constraints[constraint] {
    allow
    constraint := {
        "max_amount": input.amount,
        "currency": input.currency,
        "allowed_operations": ["refund"],
        "rate_limit": "10/hour",
        "requires_audit": input.amount > 500
    }
}

# Determine if supervisor approval is required
supervisor_required if {
    input.action == "refund"
    input.amount > 100
}

# Determine if consensus is required
consensus_required if {
    input.action == "refund"
    input.amount > 1000
}

# Risk assessment
risk_level := "low" if {
    input.amount <= 100
} else := "medium" if {
    input.amount <= 1000
} else := "high"
