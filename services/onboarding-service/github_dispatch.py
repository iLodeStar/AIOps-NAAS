"""GitHub Actions dispatch integration."""

import json
import logging
from typing import Dict, Any, Optional
import httpx

from config import settings
from models import OnboardingRequest

logger = logging.getLogger(__name__)


class GitHubDispatcher:
    """Client for dispatching GitHub Actions workflows."""
    
    def __init__(self):
        self.github_token = settings.github_token
        self.repo_owner = settings.github_repo_owner
        self.repo_name = settings.github_repo_name
        self.base_url = "https://api.github.com"
        
        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
    
    async def dispatch_workflow(
        self,
        workflow_id: str,
        request: OnboardingRequest,
        inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Dispatch a workflow using workflow_dispatch event."""
        
        if settings.use_mock_actions:
            return await self._mock_dispatch(workflow_id, request, inputs)
        
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/workflows/{workflow_id}/dispatches"
            
            # Prepare workflow inputs
            workflow_inputs = {
                "request_id": request.request_id,
                "environment": request.environment,
                "ship_id": request.ship_id or "",
                "project_name": request.project_name or "",
                "application": request.application or "",
                "overlay": request.overlay or "",
                "dry_run": str(request.dry_run).lower(),
                "canary_percent": str(request.canary_percent),
                **(inputs or {})
            }
            
            payload = {
                "ref": "main",  # or configurable
                "inputs": workflow_inputs
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 204:
                    logger.info(f"Successfully dispatched workflow {workflow_id} for request {request.request_id}")
                    return {
                        "success": True,
                        "workflow_id": workflow_id,
                        "request_id": request.request_id,
                        "inputs": workflow_inputs
                    }
                else:
                    logger.error(f"Failed to dispatch workflow: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"GitHub API error: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Error dispatching workflow: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def dispatch_repository_event(
        self,
        event_type: str,
        request: OnboardingRequest,
        client_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Dispatch a repository_dispatch event."""
        
        if settings.use_mock_actions:
            return await self._mock_repository_dispatch(event_type, request, client_payload)
        
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/dispatches"
            
            payload = {
                "event_type": event_type,
                "client_payload": {
                    "request_id": request.request_id,
                    "environment": request.environment,
                    "ship_id": request.ship_id,
                    "project_name": request.project_name,
                    "application": request.application,
                    "overlay": request.overlay,
                    "dry_run": request.dry_run,
                    "canary_percent": request.canary_percent,
                    "deployment_params": request.deployment_params,
                    **(client_payload or {})
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 204:
                    logger.info(f"Successfully dispatched repository event {event_type} for request {request.request_id}")
                    return {
                        "success": True,
                        "event_type": event_type,
                        "request_id": request.request_id,
                        "client_payload": payload["client_payload"]
                    }
                else:
                    logger.error(f"Failed to dispatch repository event: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"GitHub API error: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Error dispatching repository event: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _mock_dispatch(
        self,
        workflow_id: str,
        request: OnboardingRequest,
        inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Mock workflow dispatch for testing."""
        logger.info(f"MOCK: Dispatching workflow {workflow_id} for request {request.request_id}")
        
        mock_result = {
            "success": True,
            "mock": True,
            "workflow_id": workflow_id,
            "request_id": request.request_id,
            "inputs": {
                "request_id": request.request_id,
                "environment": request.environment,
                "ship_id": request.ship_id or "",
                "project_name": request.project_name or "",
                "application": request.application or "",
                "overlay": request.overlay or "",
                "dry_run": str(request.dry_run).lower(),
                "canary_percent": str(request.canary_percent),
                **(inputs or {})
            }
        }
        
        logger.info(f"MOCK: Workflow dispatch result: {json.dumps(mock_result, indent=2)}")
        return mock_result
    
    async def _mock_repository_dispatch(
        self,
        event_type: str,
        request: OnboardingRequest,
        client_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Mock repository dispatch for testing."""
        logger.info(f"MOCK: Dispatching repository event {event_type} for request {request.request_id}")
        
        mock_result = {
            "success": True,
            "mock": True,
            "event_type": event_type,
            "request_id": request.request_id,
            "client_payload": {
                "request_id": request.request_id,
                "environment": request.environment,
                "ship_id": request.ship_id,
                "project_name": request.project_name,
                "application": request.application,
                "overlay": request.overlay,
                "dry_run": request.dry_run,
                "canary_percent": request.canary_percent,
                "deployment_params": request.deployment_params,
                **(client_payload or {})
            }
        }
        
        logger.info(f"MOCK: Repository dispatch result: {json.dumps(mock_result, indent=2)}")
        return mock_result


# Global GitHub dispatcher instance
github_dispatcher = GitHubDispatcher()

# For testing
def get_mock_dispatcher():
    """Get mock dispatcher for testing."""
    return GitHubDispatcher()  # Use the main class with mock settings