package service_actions

import rego.v1

# Service action authorization policy

# Main allow policy
allow if {
    # User has required permissions for the action
    action_allowed
    
    # Resource-specific access granted
    resource_access_granted
    
    # Context-specific conditions met
    context_conditions_met
}

# Action-specific permissions
action_allowed if {
    input.action == "view"
    # All authenticated users can view (handled at application level)
}

action_allowed if {
    input.action == "list"
    # All authenticated users can list (with filtering)
}

action_allowed if {
    input.action == "create"
    input.user.roles[_] in ["requester", "admin"]
}

action_allowed if {
    input.action == "submit"
    input.user.roles[_] in ["requester", "admin"]
}

action_allowed if {
    input.action == "approve_deployer"
    input.user.roles[_] in ["deployer", "admin"]
}

action_allowed if {
    input.action == "approve_authoriser"
    input.user.roles[_] in ["authoriser", "admin"]
}

action_allowed if {
    input.action == "execute"
    input.user.roles[_] in ["deployer", "admin"]
}

action_allowed if {
    input.action == "audit"
    input.user.roles[_] in ["admin", "viewer"]
}

action_allowed if {
    input.action == "admin"
    "admin" in input.user.roles
}

# Resource access control
resource_access_granted if {
    # No specific resource specified
    not input.resource
}

resource_access_granted if {
    # Admin has access to all resources
    "admin" in input.user.roles
}

resource_access_granted if {
    # Users can access their own requests
    input.resource
    input.context.resource_owner == input.user.user_id
}

resource_access_granted if {
    # Viewers can access all resources for viewing
    "viewer" in input.user.roles
    input.action in ["view", "list", "audit"]
}

# Context-specific conditions
context_conditions_met if {
    # No specific context requirements
    not input.context
}

context_conditions_met if {
    # Environment-specific restrictions
    environment_access_allowed
}

# Environment access control
environment_access_allowed if {
    # Non-prod access is generally open
    input.context.environment == "nonprod"
}

environment_access_allowed if {
    # Production access requires appropriate roles
    input.context.environment == "prod"
    production_access_granted
}

environment_access_allowed if {
    # No environment specified
    not input.context.environment
}

# Production access control
production_access_granted if {
    "admin" in input.user.roles
}

production_access_granted if {
    # Deployers and authorisers can access prod for their functions
    input.user.roles[_] in ["deployer", "authoriser"]
    input.action in ["view", "list", "approve_deployer", "approve_authoriser", "execute"]
}

production_access_granted if {
    # Viewers can access prod for viewing
    "viewer" in input.user.roles
    input.action in ["view", "list", "audit"]
}

# Policy decision
decision := {
    "allowed": allow,
    "reason": reason,
    "policy": "service_actions/main"
}

# Reason for decision
reason := "Action allowed by policy" if allow

reason := "User lacks required permissions for action" if {
    not action_allowed
}

reason := "Resource access denied" if {
    action_allowed
    not resource_access_granted
}

reason := "Context conditions not met" if {
    action_allowed
    resource_access_granted
    not context_conditions_met
}

# Default reason
reason := "Action denied by policy" if {
    not allow
}