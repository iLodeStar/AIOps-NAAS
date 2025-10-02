#!/usr/bin/env python3
"""
AIOps Incident API - Extensions for Ops Console
Adds endpoints for approvals, actions, and policy management
"""

import os
import json
import yaml
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ============================================================================
# Models
# ============================================================================

class ApprovalRequest(BaseModel):
    approval_id: str
    action: str = Field(..., description="approve or reject")
    comment: str = ""

class ActionExecutionRequest(BaseModel):
    action_id: str
    incident_id: Optional[str] = None
    params: Dict[str, Any] = {}

class AuditEvent(BaseModel):
    action: str
    resource: str
    details: Dict[str, Any]

# ============================================================================
# Approvals Router
# ============================================================================

approvals_router = APIRouter(prefix="/api/approvals", tags=["approvals"])

# In-memory storage for demo (replace with database)
_approvals = []
_approval_history = []

@approvals_router.get("/pending")
async def get_pending_approvals():
    """Get all pending approvals"""
    pending = [a for a in _approvals if a.get("status") == "pending"]
    return {"data": pending}

@approvals_router.get("/mine")
async def get_my_approvals():
    """Get approvals created by current user"""
    # TODO: Get user from auth context
    user = os.getenv("USER", "operator")
    mine = [a for a in _approvals if a.get("requested_by") == user]
    return {"data": mine}

@approvals_router.post("/{approval_id}/approve")
async def approve_or_reject(approval_id: str, request: ApprovalRequest):
    """Approve or reject an action"""
    # Find approval
    approval = next((a for a in _approvals if a.get("approval_id") == approval_id), None)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    # Update approval
    user = os.getenv("USER", "operator")
    approval["status"] = "approved" if request.action == "approve" else "rejected"
    approval["approver"] = user
    approval["approved_at"] = datetime.now().isoformat()
    approval["comment"] = request.comment
    
    # If two-person required, check count
    if approval.get("requires_two_person"):
        approval["approvals_count"] = approval.get("approvals_count", 0) + 1
        if approval["approvals_count"] < approval.get("approvals_required", 2):
            approval["status"] = "pending"  # Still need more approvals
    
    # Log audit event
    _approval_history.append({
        "approval_id": approval_id,
        "action": request.action,
        "user": user,
        "timestamp": datetime.now().isoformat(),
        "comment": request.comment
    })
    
    logger.info(f"Approval {approval_id} {request.action} by {user}")
    
    return {"data": approval}

# ============================================================================
# Actions Router
# ============================================================================

actions_router = APIRouter(prefix="/api/actions", tags=["actions"])

# Action definitions (would come from policy)
_action_definitions = [
    {
        "action_id": "restart_service",
        "name": "Restart Service",
        "description": "Safely restart a failed service",
        "risk": "low",
        "allowed": True,
        "requires_approval": False,
        "requires_two_person": False,
        "cooldown_sec": 300,
        "parameters": [
            {"name": "service_name", "type": "string", "required": True},
            {"name": "force", "type": "boolean", "required": False, "default": False}
        ]
    },
    {
        "action_id": "rotate_logs",
        "name": "Rotate Logs",
        "description": "Force log rotation to free disk space",
        "risk": "low",
        "allowed": True,
        "requires_approval": False,
        "requires_two_person": False,
        "cooldown_sec": 600,
        "parameters": []
    },
    {
        "action_id": "failover_path",
        "name": "Failover to Backup Path",
        "description": "Switch to backup communication path",
        "risk": "medium",
        "allowed": True,
        "requires_approval": True,
        "requires_two_person": True,
        "cooldown_sec": 1800,
        "parameters": [
            {"name": "path", "type": "string", "required": True},
            {"name": "verify_first", "type": "boolean", "required": False, "default": True}
        ]
    }
]

_action_executions = {}
_last_executed = {}

@actions_router.get("")
async def get_available_actions():
    """Get all available actions with current status"""
    actions = []
    for action in _action_definitions:
        action_copy = action.copy()
        # Add execution status
        last_exec = _last_executed.get(action["action_id"])
        if last_exec:
            action_copy["last_executed"] = last_exec
            next_available = datetime.fromisoformat(last_exec) + timedelta(seconds=action["cooldown_sec"])
            action_copy["next_available"] = next_available.isoformat()
        actions.append(action_copy)
    
    return {"data": actions}

@actions_router.post("/execute")
async def execute_action(request: ActionExecutionRequest):
    """Execute an action with safety checks"""
    # Find action
    action = next((a for a in _action_definitions if a["action_id"] == request.action_id), None)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    # Check if allowed
    if not action.get("allowed"):
        raise HTTPException(status_code=403, detail="Action not allowed")
    
    # Check cooldown
    last_exec = _last_executed.get(request.action_id)
    if last_exec:
        last_exec_dt = datetime.fromisoformat(last_exec)
        cooldown_end = last_exec_dt + timedelta(seconds=action["cooldown_sec"])
        if datetime.now() < cooldown_end:
            raise HTTPException(
                status_code=429,
                detail=f"Action on cooldown until {cooldown_end.isoformat()}"
            )
    
    # Check if approval required
    if action.get("requires_approval"):
        # In real implementation, check approval status
        logger.info(f"Action {request.action_id} requires approval")
    
    # Create execution record
    execution_id = f"exec-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    user = os.getenv("USER", "operator")
    
    execution = {
        "execution_id": execution_id,
        "action_id": request.action_id,
        "incident_id": request.incident_id,
        "executed_by": user,
        "executed_at": datetime.now().isoformat(),
        "parameters": request.params,
        "status": "success",  # In real impl, actually execute and get result
        "result": {
            "pre_checks": {
                "service_accessible": True,
                "prerequisites_met": True
            },
            "output": f"Action {action['name']} executed successfully",
            "post_checks": {
                "service_healthy": True,
                "no_errors": True
            }
        }
    }
    
    _action_executions[execution_id] = execution
    _last_executed[request.action_id] = datetime.now().isoformat()
    
    logger.info(f"Executed action {request.action_id} by {user}")
    
    return {"data": execution}

@actions_router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Get execution result"""
    execution = _action_executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return {"data": execution}

# ============================================================================
# Policy Router
# ============================================================================

policy_router = APIRouter(prefix="/api/policy", tags=["policy"])

def load_policy_from_file():
    """Load policy from YAML file"""
    policy_file = os.getenv("POLICY_FILE", "/tmp/design_docs/policy_example.yaml")
    
    try:
        if os.path.exists(policy_file):
            with open(policy_file, 'r') as f:
                policy_data = yaml.safe_load(f)
                return policy_data
        else:
            # Return default policy structure
            return {
                "schema_version": "1.0",
                "ingest": {},
                "detect": {},
                "correlate": {},
                "notify": {},
                "remediate": {},
                "llm": {},
                "retention": {},
                "privacy": {},
                "slo": {}
            }
    except Exception as e:
        logger.error(f"Error loading policy: {e}")
        return {}

@policy_router.get("")
async def get_policy():
    """Get effective policy configuration"""
    policy_data = load_policy_from_file()
    
    # Transform into our format
    policy = {
        "schema_version": policy_data.get("schema_version", "1.0"),
        "last_updated": datetime.now().isoformat(),
        "source": "local",
        "sections": {}
    }
    
    # Map sections
    for section_name in ["ingest", "detect", "correlate", "notify", "remediate", "llm", "retention", "privacy", "slo"]:
        if section_name in policy_data:
            policy["sections"][section_name] = {
                "name": section_name,
                "values": policy_data[section_name],
                "source": "default",
                "effective": True
            }
    
    return {"data": policy}

@policy_router.get("/diff")
async def get_policy_diff():
    """Get diff between ship policy and fleet default"""
    # In real implementation, compare with fleet policy from shore
    return {
        "data": {
            "has_changes": False,
            "diff": "No differences from fleet default"
        }
    }

# ============================================================================
# Audit Router
# ============================================================================

audit_router = APIRouter(prefix="/api/audit", tags=["audit"])

_audit_log = []

@audit_router.post("")
async def log_audit_event(event: AuditEvent):
    """Log an audit event"""
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "user": os.getenv("USER", "operator"),
        "action": event.action,
        "resource": event.resource,
        "details": event.details
    }
    
    _audit_log.append(audit_entry)
    logger.info(f"Audit: {event.action} on {event.resource} by {audit_entry['user']}")
    
    # In real implementation, publish to ops.audit NATS subject
    
    return {"data": audit_entry}

@audit_router.get("")
async def get_audit_log(limit: int = 100):
    """Get recent audit log entries"""
    return {"data": _audit_log[-limit:]}
