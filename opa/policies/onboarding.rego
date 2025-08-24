package onboarding

import rego.v1

# Two-level approval policy for onboarding requests

# Main approval policy
approval := {
    "allowed": allow,
    "reason": reason,
    "requires_second_approval": requires_second_approval
}

# Allow approval if all conditions are met
allow if {
    # User has required role
    has_required_role
    
    # User is not the requester
    not is_requester
    
    # User hasn't already approved in this role
    not already_approved_in_role
    
    # Role-specific conditions
    role_specific_allowed
}

# Check if user has the required role for approval
has_required_role if {
    input.approval.role == "deployer"
    "deployer" in input.user.roles
}

has_required_role if {
    input.approval.role == "deployer" 
    "admin" in input.user.roles
}

has_required_role if {
    input.approval.role == "authoriser"
    "authoriser" in input.user.roles
}

has_required_role if {
    input.approval.role == "authoriser"
    "admin" in input.user.roles
}

# Check if user is the original requester
is_requester if {
    input.user.user_id == input.request.requester_id
}

# Check if user has already approved in this role
already_approved_in_role if {
    approval := input.approval.existing_approvals[_]
    approval.approver_id == input.user.user_id
    approval.role == input.approval.role
}

# Role-specific approval conditions
role_specific_allowed if {
    input.approval.role == "deployer"
    # Deployer can approve at any time after submission
    input.request.status in ["submitted", "authoriser_approved"]
}

role_specific_allowed if {
    input.approval.role == "authoriser"
    # Authoriser can approve at any time after submission
    input.request.status in ["submitted", "deployer_approved"]
}

# Check if second approval is required
requires_second_approval if {
    # Always require both deployer and authoriser approval
    true
}

# Environment-specific rules
environment_rules := {
    "nonprod": {
        "approval_timeout_hours": 168,  # 1 week
        "change_window_required": false,
        "additional_restrictions": []
    },
    "prod": {
        "approval_timeout_hours": 24,   # 1 day
        "change_window_required": true,
        "additional_restrictions": ["business_hours_only"]
    }
}

# Execution policy
execution := {
    "allowed": execution_allowed,
    "reason": execution_reason,
    "constraints": execution_constraints
}

# Allow execution if all conditions are met
execution_allowed if {
    # User has execution permissions
    has_execution_role
    
    # Two-level approval requirements satisfied
    two_level_approval_satisfied
    
    # Environment-specific requirements met
    environment_requirements_met
    
    # No policy violations
    not has_policy_violations
}

# Check if user has execution role
has_execution_role if {
    "admin" in input.user.roles
}

has_execution_role if {
    "deployer" in input.user.roles
}

# Check two-level approval requirements
two_level_approval_satisfied if {
    # Must have approvals from both deployer and authoriser
    deployer_approvals := [approval | approval := input.approvals[_]; approval.role == "deployer"]
    authoriser_approvals := [approval | approval := input.approvals[_]; approval.role == "authoriser"]
    
    count(deployer_approvals) > 0
    count(authoriser_approvals) > 0
    
    # Approvers must be distinct users
    deployer_ids := {approval.approver_id | approval := deployer_approvals[_]}
    authoriser_ids := {approval.approver_id | approval := authoriser_approvals[_]}
    
    count(deployer_ids & authoriser_ids) == 0
    
    # Neither approver can be the original requester
    all_approver_ids := deployer_ids | authoriser_ids
    not input.request.requester_id in all_approver_ids
}

# Environment-specific requirements
environment_requirements_met if {
    input.request.environment == "nonprod"
    # Non-prod is more permissive
}

environment_requirements_met if {
    input.request.environment == "prod"
    
    # Production requires recent approvals
    recent_approvals_only
    
    # Production may require change window (if configured)
    change_window_satisfied
}

# Check that approvals are recent for production
recent_approvals_only if {
    input.request.environment != "prod"
}

recent_approvals_only if {
    input.request.environment == "prod"
    
    # Check that all approvals are within timeout
    timeout_hours := environment_rules[input.request.environment].approval_timeout_hours
    
    # For each approval, check if it's recent enough
    every approval in input.approvals {
        approval_age_valid(approval, timeout_hours)
    }
}

# Helper to check approval age
approval_age_valid(approval, timeout_hours) if {
    # In a real implementation, this would parse the timestamp and check against current time
    # For now, assume all approvals are recent in mock mode
    true
}

# Change window satisfaction (simplified for MVP)
change_window_satisfied if {
    # For MVP, assume change window is always satisfied
    # In production, this would check against configured maintenance windows
    true
}

# Policy violations check
has_policy_violations if {
    # Check for any blockers
    input.request.environment == "prod"
    not business_hours
    environment_rules[input.request.environment].additional_restrictions[_] == "business_hours_only"
}

# Business hours check (simplified)
business_hours if {
    # For MVP, assume always in business hours
    # In production, this would check current time against configured business hours
    true
}

# Execution constraints
execution_constraints := {
    "dry_run_required": dry_run_required,
    "max_execution_time_minutes": max_execution_time,
    "rollback_required": rollback_required,
    "notification_required": true
}

# Require dry run for certain conditions
dry_run_required if {
    input.request.environment == "prod"
    input.request.dry_run == false
    # Production deployments should default to dry run first
}

# Maximum execution time based on environment
max_execution_time := 30 if {
    input.request.environment == "nonprod"
}

max_execution_time := 60 if {
    input.request.environment == "prod"
}

# Rollback requirements
rollback_required if {
    input.request.environment == "prod"
}

# Reason for execution decision
execution_reason := "Execution approved - all requirements satisfied" if execution_allowed

execution_reason := "User lacks execution permissions" if {
    not has_execution_role
}

execution_reason := "Two-level approval requirements not satisfied" if {
    not two_level_approval_satisfied
}

execution_reason := "Environment requirements not met" if {
    not environment_requirements_met
}

execution_reason := "Policy violations detected" if {
    has_policy_violations
}

# Default reason
execution_reason := "Execution denied by policy" if {
    not execution_allowed
}

# Reason for approval decision
reason := "Approval allowed" if allow

reason := "User lacks required role" if {
    not has_required_role
}

reason := "User cannot approve their own request" if {
    is_requester
}

reason := "User has already approved in this role" if {
    already_approved_in_role
}

reason := "Role-specific conditions not met" if {
    has_required_role
    not is_requester
    not already_approved_in_role
    not role_specific_allowed
}

# Default reason
reason := "Approval denied by policy" if {
    not allow
}