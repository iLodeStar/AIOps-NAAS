"""Integration test for onboarding service end-to-end workflow."""

import asyncio
import json
import logging
from datetime import datetime
import requests
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OnboardingServiceTester:
    """Test the complete onboarding workflow."""
    
    def __init__(self, base_url: str = "http://localhost:8090"):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Test users
        self.users = {
            "requester": {"user_id": "req1", "email": "req1@cruise.com", "roles": ["requester"]},
            "deployer": {"user_id": "dep1", "email": "dep1@cruise.com", "roles": ["deployer"]},
            "authoriser": {"user_id": "auth1", "email": "auth1@cruise.com", "roles": ["authoriser"]},
            "admin": {"user_id": "admin1", "email": "admin1@cruise.com", "roles": ["admin"]}
        }
    
    def create_test_token(self, user_type: str) -> str:
        """Create test token for user type."""
        from auth import create_test_token
        user = self.users[user_type]
        return create_test_token(user["user_id"], user["roles"])
    
    def test_health_check(self) -> bool:
        """Test health check endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✓ Health check passed: {data}")
                return True
            else:
                logger.error(f"✗ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"✗ Health check error: {e}")
            return False
    
    def test_create_request(self) -> str:
        """Test creating a request."""
        try:
            token = self.create_test_token("admin")  # Use admin for simplicity
            headers = {"Authorization": f"Bearer {token}"}
            
            request_data = {
                "title": "Test Integration Request",
                "description": "Test request for integration testing",
                "ship_id": "test-ship-01",
                "project_name": "integration-test",
                "environment": "nonprod",
                "application": "test-app",
                "overlay": "test-overlay",
                "dry_run": True,
                "canary_percent": 10
            }
            
            response = self.session.post(
                f"{self.base_url}/api/requests",
                json=request_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                request_id = data["request_id"]
                logger.info(f"✓ Request created: {request_id}")
                return request_id
            else:
                logger.error(f"✗ Request creation failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"✗ Request creation error: {e}")
            return None
    
    def test_submit_request(self, request_id: str) -> bool:
        """Test submitting a request."""
        try:
            token = self.create_test_token("admin")
            headers = {"Authorization": f"Bearer {token}"}
            
            response = self.session.post(
                f"{self.base_url}/api/requests/{request_id}/submit",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✓ Request submitted: {data}")
                return True
            else:
                logger.error(f"✗ Request submission failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Request submission error: {e}")
            return False
    
    def test_approval_workflow(self, request_id: str) -> bool:
        """Test two-level approval workflow."""
        try:
            # Deployer approval
            token = self.create_test_token("admin")  # Using admin token for both roles in test
            headers = {"Authorization": f"Bearer {token}"}
            
            approval_data = {
                "role": "deployer",
                "decision": "approved",
                "comments": "Deployer approval for integration test"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/requests/{request_id}/approve",
                json=approval_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"✗ Deployer approval failed: {response.status_code} - {response.text}")
                return False
            
            logger.info("✓ Deployer approval successful")
            
            # Authoriser approval
            approval_data = {
                "role": "authoriser",
                "decision": "approved", 
                "comments": "Authoriser approval for integration test"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/requests/{request_id}/approve",
                json=approval_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"✗ Authoriser approval failed: {response.status_code} - {response.text}")
                return False
            
            logger.info("✓ Authoriser approval successful")
            return True
            
        except Exception as e:
            logger.error(f"✗ Approval workflow error: {e}")
            return False
    
    def test_execution(self, request_id: str) -> bool:
        """Test request execution."""
        try:
            token = self.create_test_token("admin")
            headers = {"Authorization": f"Bearer {token}"}
            
            response = self.session.post(
                f"{self.base_url}/api/requests/{request_id}/execute",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✓ Request execution successful: {data}")
                return True
            else:
                logger.error(f"✗ Request execution failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Request execution error: {e}")
            return False
    
    def test_audit_export(self, request_id: str) -> bool:
        """Test audit log export."""
        try:
            token = self.create_test_token("admin")
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test JSON export
            response = self.session.get(
                f"{self.base_url}/api/audit/{request_id}?format=json",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                audit_data = response.json()
                logger.info(f"✓ Audit export successful: {len(audit_data)} entries")
                return True
            else:
                logger.error(f"✗ Audit export failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Audit export error: {e}")
            return False
    
    def run_complete_workflow(self) -> bool:
        """Run complete end-to-end test workflow."""
        logger.info("Starting complete onboarding workflow test...")
        
        # Test 1: Health check
        if not self.test_health_check():
            return False
        
        # Test 2: Create request
        request_id = self.test_create_request()
        if not request_id:
            return False
        
        # Test 3: Submit request
        if not self.test_submit_request(request_id):
            return False
        
        # Test 4: Approval workflow
        if not self.test_approval_workflow(request_id):
            return False
        
        # Test 5: Execute request
        if not self.test_execution(request_id):
            return False
        
        # Test 6: Audit export
        if not self.test_audit_export(request_id):
            return False
        
        logger.info("🎉 Complete workflow test passed!")
        return True


def test_standalone():
    """Test service components without running server."""
    logger.info("Testing standalone components...")
    
    try:
        # Add parent directory to path for imports
        import sys
        import os
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Test imports
        from app import app
        from models import OnboardingRequest, RequestStatus, UserRole
        from auth import UserInfo, create_test_token
        from opa_client import MockOPAClient
        
        logger.info("✓ All imports successful")
        
        # Test user info
        user = UserInfo("test_user", "test@cruise.com", "Test User", ["admin"])
        assert user.is_admin()
        assert user.can_approve_as_deployer()
        assert user.can_approve_as_authoriser()
        logger.info("✓ User info tests passed")
        
        # Test token creation
        token = create_test_token("test_user", ["admin"])
        assert isinstance(token, str)
        assert len(token) > 0
        logger.info("✓ Token creation tests passed")
        
        # Test OPA client
        opa = MockOPAClient()
        test_input = {
            "user": {"user_id": "test", "roles": ["admin"]},
            "action": "create"
        }
        
        # Use asyncio for async test
        async def test_opa():
            result = await opa.evaluate_policy("service_actions/allow", test_input)
            assert result["allowed"] == True
            return True
        
        asyncio.run(test_opa())
        logger.info("✓ OPA client tests passed")
        
        logger.info("🎉 All standalone tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Standalone test error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # Test against running server
        tester = OnboardingServiceTester()
        success = tester.run_complete_workflow()
    else:
        # Test standalone components
        success = test_standalone()
    
    sys.exit(0 if success else 1)