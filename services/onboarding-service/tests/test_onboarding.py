"""Unit tests for onboarding service."""

import pytest
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os

# Add current directory to path
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import app
from models import Base, OnboardingRequest, Approval, AuditLog, RequestStatus, UserRole
from db import get_db
from auth import get_current_user, UserInfo, create_test_token
from opa_client import MockOPAClient
from github_dispatch import get_mock_dispatcher

# Test database setup
def create_test_db():
    """Create test database."""
    db_file = tempfile.NamedTemporaryFile(delete=False)
    db_file.close()
    engine = create_engine(f"sqlite:///{db_file.name}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine, db_file.name

@pytest.fixture
def test_db():
    """Test database fixture."""
    engine, db_path = create_test_db()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestingSessionLocal
    
    # Cleanup
    app.dependency_overrides.clear()
    os.unlink(db_path)

@pytest.fixture
def test_user():
    """Test user fixture."""
    return UserInfo(
        user_id="test_user",
        email="test@cruise.com",
        name="Test User",
        roles=[UserRole.REQUESTER.value, UserRole.DEPLOYER.value]
    )

@pytest.fixture
def admin_user():
    """Admin user fixture."""
    return UserInfo(
        user_id="admin_user",
        email="admin@cruise.com",
        name="Admin User",
        roles=[UserRole.ADMIN.value]
    )

@pytest.fixture
def authoriser_user():
    """Authoriser user fixture."""
    return UserInfo(
        user_id="auth_user",
        email="auth@cruise.com",
        name="Authoriser User",
        roles=[UserRole.AUTHORISER.value]
    )

@pytest.fixture
def client(test_db):
    """Test client fixture."""
    
    def mock_get_current_user():
        return UserInfo(
            user_id="test_user",
            email="test@cruise.com",
            name="Test User",
            roles=[UserRole.ADMIN.value]  # Admin for test simplicity
        )
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


class TestOnboardingService:
    """Test suite for onboarding service."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "onboarding-service"
    
    def test_create_request(self, client, test_db):
        """Test creating an onboarding request."""
        request_data = {
            "title": "Test Onboarding Request",
            "description": "Test description",
            "ship_id": "test-ship-01",
            "project_name": "test-project",
            "environment": "nonprod",
            "application": "test-app",
            "overlay": "test-overlay",
            "dry_run": True,
            "canary_percent": 10
        }
        
        response = client.post("/api/requests", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == request_data["title"]
        assert data["status"] == RequestStatus.DRAFT.value
        assert data["requester_id"] == "test_user"
    
    def test_submit_request(self, client, test_db):
        """Test submitting a request for approval."""
        # First create a request
        request_data = {
            "title": "Test Submit Request",
            "environment": "nonprod"
        }
        
        create_response = client.post("/api/requests", json=request_data)
        assert create_response.status_code == 200
        request_id = create_response.json()["request_id"]
        
        # Submit the request
        submit_response = client.post(f"/api/requests/{request_id}/submit")
        assert submit_response.status_code == 200
        assert submit_response.json()["status"] == RequestStatus.SUBMITTED.value
    
    def test_list_requests(self, client, test_db):
        """Test listing requests."""
        # Create a few test requests
        for i in range(3):
            request_data = {
                "title": f"Test Request {i+1}",
                "environment": "nonprod"
            }
            client.post("/api/requests", json=request_data)
        
        # List requests
        response = client.get("/api/requests")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 3
        assert all(req["title"].startswith("Test Request") for req in data)
    
    def test_get_request(self, client, test_db):
        """Test getting a specific request."""
        # Create a request
        request_data = {
            "title": "Test Get Request",
            "environment": "nonprod"
        }
        
        create_response = client.post("/api/requests", json=request_data)
        request_id = create_response.json()["request_id"]
        
        # Get the request
        response = client.get(f"/api/requests/{request_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["request_id"] == request_id
        assert data["title"] == request_data["title"]
    
    def test_approval_workflow(self, client, test_db):
        """Test the two-level approval workflow."""
        # Create and submit a request
        request_data = {
            "title": "Test Approval Workflow",
            "environment": "nonprod"
        }
        
        create_response = client.post("/api/requests", json=request_data)
        request_id = create_response.json()["request_id"]
        
        # Submit for approval
        client.post(f"/api/requests/{request_id}/submit")
        
        # Mock different users for approvals
        def mock_deployer_user():
            return UserInfo(
                user_id="deployer_user",
                email="deployer@cruise.com", 
                name="Deployer User",
                roles=[UserRole.DEPLOYER.value]
            )
        
        def mock_authoriser_user():
            return UserInfo(
                user_id="auth_user",
                email="auth@cruise.com",
                name="Authoriser User", 
                roles=[UserRole.AUTHORISER.value]
            )
        
        # First approval (deployer)
        app.dependency_overrides[get_current_user] = mock_deployer_user
        
        approval_data = {
            "role": "deployer",
            "decision": "approved",
            "comments": "Deployer approval"
        }
        
        response = client.post(f"/api/requests/{request_id}/approve", json=approval_data)
        assert response.status_code == 200
        
        # Second approval (authoriser)
        app.dependency_overrides[get_current_user] = mock_authoriser_user
        
        approval_data = {
            "role": "authoriser", 
            "decision": "approved",
            "comments": "Authoriser approval"
        }
        
        response = client.post(f"/api/requests/{request_id}/approve", json=approval_data)
        assert response.status_code == 200
        
        # Check final status
        response = client.get(f"/api/requests/{request_id}")
        assert response.json()["status"] == RequestStatus.APPROVED.value


class TestOPAPolicies:
    """Test OPA policy logic."""
    
    @pytest.mark.asyncio
    async def test_mock_opa_approval_policy(self):
        """Test mock OPA approval policy."""
        opa = MockOPAClient()
        
        # Test valid approval
        input_data = {
            "user": {
                "user_id": "deployer1",
                "email": "deployer1@cruise.com",
                "roles": ["deployer"]
            },
            "request": {
                "requester_id": "requester1",
                "status": "submitted"
            },
            "approval": {
                "role": "deployer",
                "existing_approvals": []
            }
        }
        
        result = await opa.evaluate_policy("onboarding/approval", input_data)
        assert result["allowed"] == True
        
        # Test self-approval rejection
        input_data["user"]["user_id"] = "requester1"
        result = await opa.evaluate_policy("onboarding/approval", input_data)
        assert result["allowed"] == False
        assert "own request" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_mock_opa_execution_policy(self):
        """Test mock OPA execution policy."""
        opa = MockOPAClient()
        
        # Test valid execution with two approvals
        input_data = {
            "user": {
                "user_id": "executor1",
                "email": "executor1@cruise.com",
                "roles": ["deployer"]
            },
            "request": {
                "requester_id": "requester1",
                "environment": "nonprod"
            },
            "approvals": [
                {
                    "role": "deployer",
                    "approver_id": "deployer1",
                    "approved_at": "2024-01-01T10:00:00Z"
                },
                {
                    "role": "authoriser",
                    "approver_id": "auth1",
                    "approved_at": "2024-01-01T10:30:00Z"
                }
            ]
        }
        
        result = await opa.evaluate_policy("onboarding/execution", input_data)
        assert result["allowed"] == True
        
        # Test execution without sufficient approvals
        input_data["approvals"] = [
            {
                "role": "deployer", 
                "approver_id": "deployer1",
                "approved_at": "2024-01-01T10:00:00Z"
            }
        ]
        
        result = await opa.evaluate_policy("onboarding/execution", input_data)
        assert result["allowed"] == False
        assert "authoriser approval" in result["reason"]


class TestAuthPermissions:
    """Test authentication and authorization."""
    
    def test_user_role_checks(self):
        """Test user role checking methods."""
        user = UserInfo(
            user_id="test_user",
            email="test@cruise.com",
            name="Test User",
            roles=[UserRole.DEPLOYER.value, UserRole.REQUESTER.value]
        )
        
        assert user.has_role(UserRole.DEPLOYER)
        assert user.has_role(UserRole.REQUESTER)
        assert not user.has_role(UserRole.ADMIN)
        assert not user.is_admin()
        assert user.can_approve_as_deployer()
        assert not user.can_approve_as_authoriser()
    
    def test_admin_permissions(self):
        """Test admin user permissions."""
        admin = UserInfo(
            user_id="admin_user",
            email="admin@cruise.com", 
            name="Admin User",
            roles=[UserRole.ADMIN.value]
        )
        
        assert admin.is_admin()
        assert admin.can_approve_as_deployer()
        assert admin.can_approve_as_authoriser()
        assert admin.can_execute_deployment()
    
    def test_token_creation_and_verification(self):
        """Test session token creation and verification."""
        from auth import create_session_token, verify_session_token
        
        user = UserInfo(
            user_id="token_test",
            email="token@cruise.com",
            name="Token User",
            roles=[UserRole.VIEWER.value]
        )
        
        # Create token
        token = create_session_token(user)
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token
        verified_user = verify_session_token(token)
        assert verified_user is not None
        assert verified_user.user_id == user.user_id
        assert verified_user.email == user.email
        assert verified_user.roles == user.roles


if __name__ == "__main__":
    pytest.main([__file__, "-v"])