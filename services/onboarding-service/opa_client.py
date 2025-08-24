"""OPA (Open Policy Agent) client for authorization decisions."""

import json
import logging
from typing import Dict, Any, Optional, List
import httpx

from config import settings
from models import OnboardingRequest, Approval, UserRole
from auth import UserInfo

logger = logging.getLogger(__name__)


class OPAClient:
    """Client for communicating with OPA server."""
    
    def __init__(self, opa_url: str = None):
        self.opa_url = opa_url or settings.opa_url
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def evaluate_policy(self, policy_path: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate policy with input data."""
        try:
            url = f"{self.opa_url}/v1/data/{policy_path}"
            
            response = await self.client.post(
                url,
                json={"input": input_data},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("result", {})
            else:
                logger.error(f"OPA policy evaluation failed: {response.status_code} - {response.text}")
                # Default to deny if OPA is unavailable
                return {"allowed": False, "reason": "Policy evaluation failed"}
                
        except Exception as e:
            logger.error(f"Error communicating with OPA: {e}")
            # Default to deny if OPA is unavailable
            return {"allowed": False, "reason": f"OPA communication error: {str(e)}"}
    
    async def can_approve_request(
        self, 
        user: UserInfo, 
        request: OnboardingRequest, 
        approval_role: str,
        existing_approvals: List[Approval]
    ) -> Dict[str, Any]:
        """Check if user can approve a request in a specific role."""
        
        input_data = {
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "roles": user.roles
            },
            "request": {
                "request_id": request.request_id,
                "environment": request.environment,
                "requester_id": request.requester_id,
                "status": request.status
            },
            "approval": {
                "role": approval_role,
                "existing_approvals": [
                    {
                        "role": a.role,
                        "approver_id": a.approver_id,
                        "decision": a.decision
                    } for a in existing_approvals
                ]
            }
        }
        
        return await self.evaluate_policy("onboarding/approval", input_data)
    
    async def can_execute_request(
        self,
        user: UserInfo,
        request: OnboardingRequest,
        approvals: List[Approval]
    ) -> Dict[str, Any]:
        """Check if request can be executed."""
        
        input_data = {
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "roles": user.roles
            },
            "request": {
                "request_id": request.request_id,
                "environment": request.environment,
                "requester_id": request.requester_id,
                "status": request.status,
                "ship_id": request.ship_id,
                "application": request.application
            },
            "approvals": [
                {
                    "role": a.role,
                    "approver_id": a.approver_id,
                    "decision": a.decision,
                    "approved_at": a.created_at.isoformat()
                } for a in approvals if a.decision == "approved"
            ]
        }
        
        return await self.evaluate_policy("onboarding/execution", input_data)
    
    async def can_perform_action(
        self,
        user: UserInfo,
        action: str,
        resource: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check if user can perform a general action."""
        
        input_data = {
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "roles": user.roles
            },
            "action": action,
            "resource": resource,
            "context": context or {}
        }
        
        return await self.evaluate_policy("service_actions/allow", input_data)
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Global OPA client instance
opa_client = OPAClient()


# Mock OPA client for testing
class MockOPAClient(OPAClient):
    """Mock OPA client for testing purposes."""
    
    def __init__(self):
        self.opa_url = "mock://opa"
        # Don't initialize HTTP client for mock
    
    async def evaluate_policy(self, policy_path: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock policy evaluation with basic rules."""
        
        if policy_path == "onboarding/approval":
            return self._mock_approval_policy(input_data)
        elif policy_path == "onboarding/execution":
            return self._mock_execution_policy(input_data)
        elif policy_path == "service_actions/allow":
            return self._mock_action_policy(input_data)
        else:
            return {"allowed": False, "reason": "Unknown policy"}
    
    def _mock_approval_policy(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock approval policy logic."""
        user = input_data["user"]
        request = input_data["request"]
        approval = input_data["approval"]
        
        # Check if user has required role
        required_role = approval["role"]
        if required_role not in user["roles"] and "admin" not in user["roles"]:
            return {
                "allowed": False,
                "reason": f"User lacks required role: {required_role}"
            }
        
        # Check if user is not the requester
        if user["user_id"] == request["requester_id"]:
            return {
                "allowed": False,
                "reason": "User cannot approve their own request"
            }
        
        # Check if user hasn't already approved in this role
        existing_approvals = approval["existing_approvals"]
        for existing in existing_approvals:
            if existing["approver_id"] == user["user_id"] and existing["role"] == required_role:
                return {
                    "allowed": False,
                    "reason": "User has already provided approval in this role"
                }
        
        return {
            "allowed": True,
            "reason": "Approval allowed",
            "requires_second_approval": True
        }
    
    def _mock_execution_policy(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock execution policy logic."""
        user = input_data["user"]
        request = input_data["request"]
        approvals = input_data["approvals"]
        
        # Check if user can execute deployments
        if not any(role in user["roles"] for role in ["admin", "deployer"]):
            return {
                "allowed": False,
                "reason": "User lacks deployment execution permissions"
            }
        
        # Check for two-level approvals
        deployer_approvals = [a for a in approvals if a["role"] == "deployer"]
        authoriser_approvals = [a for a in approvals if a["role"] == "authoriser"]
        
        if not deployer_approvals:
            return {
                "allowed": False,
                "reason": "Missing deployer approval"
            }
        
        if not authoriser_approvals:
            return {
                "allowed": False,
                "reason": "Missing authoriser approval"
            }
        
        # Check for distinct approvers
        deployer_ids = {a["approver_id"] for a in deployer_approvals}
        authoriser_ids = {a["approver_id"] for a in authoriser_approvals}
        
        if deployer_ids.intersection(authoriser_ids):
            return {
                "allowed": False,
                "reason": "Deployer and authoriser must be different users"
            }
        
        # Production environment has additional checks
        if request["environment"] == "prod":
            # In production, require both approvals to be recent (within 24 hours)
            from datetime import datetime, timedelta
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            
            for approval in approvals:
                approval_time = datetime.fromisoformat(approval["approved_at"].replace("Z", "+00:00"))
                if approval_time < recent_cutoff:
                    return {
                        "allowed": False,
                        "reason": "Approval expired (older than 24 hours for production)"
                    }
        
        return {
            "allowed": True,
            "reason": "Two-level approval requirements satisfied"
        }
    
    def _mock_action_policy(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock general action policy."""
        user = input_data["user"]
        action = input_data["action"]
        
        # Admin can do everything
        if "admin" in user["roles"]:
            return {"allowed": True, "reason": "Admin privileges"}
        
        # Basic role-based permissions
        role_permissions = {
            "viewer": ["view", "list"],
            "requester": ["view", "list", "create", "submit"],
            "deployer": ["view", "list", "approve_deployer", "execute"],
            "authoriser": ["view", "list", "approve_authoriser"],
        }
        
        allowed_actions = []
        for role in user["roles"]:
            allowed_actions.extend(role_permissions.get(role, []))
        
        if action in allowed_actions:
            return {"allowed": True, "reason": f"Action allowed by role"}
        
        return {
            "allowed": False,
            "reason": f"Action '{action}' not permitted for user roles: {user['roles']}"
        }
    
    async def close(self):
        """Mock close - no-op."""
        pass