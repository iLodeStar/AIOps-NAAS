package remediation

import rego.v1

# Main allow policy for remediation actions
allow if {
    input.action.risk_level in data.allowed_risk_levels
    not rate_limit_exceeded
    not in_maintenance_window
    preconditions_met
}

# Risk level configuration
allowed_risk_levels := ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Rate limiting check
rate_limit_exceeded if {
    action_type := input.action.action_type
    recent_count := input.context.recent_actions_count
    max_allowed := action_limits[action_type].max_per_hour
    recent_count >= max_allowed
}

# Action-specific limits
action_limits := {
    "failover_backup_satellite": {"max_per_hour": 2, "requires_approval": true},
    "qos_traffic_shaping": {"max_per_hour": 5, "requires_approval": false},
    "bandwidth_reduction": {"max_per_hour": 10, "requires_approval": false},
    "antenna_realignment": {"max_per_hour": 3, "requires_approval": true},
    "power_adjustment": {"max_per_hour": 8, "requires_approval": false},
    "error_correction_increase": {"max_per_hour": 15, "requires_approval": false},
    "configuration_rollback": {"max_per_hour": 5, "requires_approval": true}
}

# Maintenance window check (simplified)
in_maintenance_window if {
    # No maintenance windows configured for MVP
    false
}

# Preconditions check
preconditions_met if {
    # All preconditions satisfied for MVP
    true
}

# Determine if approval is required
requires_approval if {
    action_type := input.action.action_type
    action_limits[action_type].requires_approval == true
}

requires_approval if {
    input.action.risk_level == "CRITICAL"
}

# Risk assessment
risk_assessment := {
    "risk_level": input.action.risk_level,
    "estimated_impact": impact_assessment,
    "rollback_available": input.action.supports_rollback,
    "dry_run_tested": input.action.supports_dry_run
}

# Impact assessment based on action type
impact_assessment := "low" if {
    input.action.action_type in ["qos_traffic_shaping", "bandwidth_reduction", "error_correction_increase"]
}

impact_assessment := "medium" if {
    input.action.action_type in ["power_adjustment", "antenna_realignment"]
}

impact_assessment := "high" if {
    input.action.action_type in ["failover_backup_satellite", "configuration_rollback"]
}

# Constraints for execution
constraints := {
    "max_execution_time": input.action.max_execution_time_minutes,
    "requires_dry_run": requires_dry_run_first,
    "rollback_timeout_minutes": 15
}

# Require dry run for high-risk actions
requires_dry_run_first if {
    input.action.risk_level in ["HIGH", "CRITICAL"]
    input.action.supports_dry_run
}

# Policy decision output
decision := {
    "allowed": allow,
    "reason": reason,
    "policy": "remediation/main",
    "requires_approval": requires_approval,
    "risk_assessment": risk_assessment,
    "constraints": constraints
}

# Reason for decision
reason := "Action approved by policy" if allow
reason := "Rate limit exceeded" if rate_limit_exceeded
reason := sprintf("Risk level %s not allowed", [input.action.risk_level]) if {
    not input.action.risk_level in allowed_risk_levels
}
reason := "In maintenance window" if in_maintenance_window
reason := "Preconditions not met" if not preconditions_met