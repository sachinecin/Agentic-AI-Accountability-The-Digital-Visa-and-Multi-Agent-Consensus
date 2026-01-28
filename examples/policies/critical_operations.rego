package digital_visa.critical_operations

import future.keywords.if
import future.keywords.in

# List of critical operations requiring special handling
critical_operations := [
    "wire_transfer",
    "account_closure",
    "large_payment",
    "privilege_escalation",
    "data_export",
    "security_config_change"
]

# Default deny all critical operations
default allow = false

# Allow critical operations only with Byzantine consensus
allow if {
    input.action in critical_operations
    input.consensus_achieved == true
    input.consensus_ratio >= 0.67
    input.agent_reputation >= 0.8
    valid_reasoning
    no_suspicious_patterns
}

# Additional check for wire transfers
allow if {
    input.action == "wire_transfer"
    input.amount <= 10000
    input.consensus_achieved == true
    input.consensus_ratio >= 0.67
    input.agent_reputation >= 0.9
    input.supervisor_approved == true
    valid_destination
    valid_reasoning
}

# Validate wire transfer destination
valid_destination if {
    input.action == "wire_transfer"
    input.destination_account != ""
    input.destination_verified == true
}

# Validate reasoning trace
valid_reasoning if {
    count(input.reasoning_trace.chain_of_thought) >= 5
    input.reasoning_trace.intent != ""
    input.task_hash != ""
}

# Check for suspicious patterns
no_suspicious_patterns if {
    not rapid_succession
    not off_hours
    not unusual_amount
}

rapid_succession if {
    input.context.recent_operations_count > 10
    input.context.time_window_minutes < 60
}

off_hours if {
    input.context.time_of_day == "night"
    input.amount > 50000
}

unusual_amount if {
    input.amount > input.context.agent_avg_amount * 10
}

# Generate constraints for approved operations
constraints[constraint] {
    allow
    constraint := {
        "operation": input.action,
        "max_retries": 0,
        "requires_audit": true,
        "requires_notification": true,
        "consensus_required": true,
        "min_consensus_ratio": 0.67,
        "immutable_trace": true,
        "ttl_seconds": 30
    }
}

# Minimum number of consensus agents required
min_consensus_agents := 3 if {
    input.action in critical_operations
    input.amount > 10000
} else := 2

# Required approver levels
required_approvers[approver] {
    input.action in critical_operations
    approver := "senior_supervisor"
}

required_approvers[approver] {
    input.action == "wire_transfer"
    input.amount > 50000
    approver := "cfo"
}

# Alert configuration
alert_required if {
    input.action in critical_operations
}

alert_urgency := "critical" if {
    input.action == "wire_transfer"
    input.amount > 100000
} else := "high" if {
    input.action in critical_operations
} else := "medium"
