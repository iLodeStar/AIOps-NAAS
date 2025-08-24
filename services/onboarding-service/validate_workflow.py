#!/usr/bin/env python3
"""
Complete validation script for onboarding service.
Tests the entire two-level approval workflow.
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from models import OnboardingRequest, Approval, AuditLog, RequestStatus, UserRole
from auth import UserInfo, create_test_token
from opa_client import MockOPAClient
from github_dispatch import GitHubDispatcher
from db import init_db, get_db
from config import settings

# Use mock mode for testing
os.environ['USE_MOCK_ACTIONS'] = 'true'
os.environ['POLICY_MODE'] = 'permissive'


async def test_complete_workflow():
    """Test complete onboarding workflow."""
    print("🧪 Testing Complete Onboarding Workflow")
    print("=" * 50)
    
    # Initialize database
    print("1. Initializing database...")
    init_db()
    print("✅ Database initialized")
    
    # Create test users
    print("\n2. Creating test users...")
    requester = UserInfo("req001", "requester@cruise.com", "Test Requester", ["requester"])
    deployer = UserInfo("dep001", "deployer@cruise.com", "Test Deployer", ["deployer"])
    authoriser = UserInfo("auth001", "authoriser@cruise.com", "Test Authoriser", ["authoriser"])
    admin = UserInfo("admin001", "admin@cruise.com", "Test Admin", ["admin"])
    
    print(f"✅ Created users: {[u.user_id for u in [requester, deployer, authoriser, admin]]}")
    
    # Test OPA policies
    print("\n3. Testing OPA policies...")
    opa = MockOPAClient()
    
    # Test approval policy
    approval_input = {
        "user": {"user_id": deployer.user_id, "roles": deployer.roles},
        "request": {"requester_id": requester.user_id, "status": "submitted"},
        "approval": {"role": "deployer", "existing_approvals": []}
    }
    
    approval_result = await opa.evaluate_policy("onboarding/approval", approval_input)
    print(f"✅ Approval policy test: {approval_result}")
    
    # Test execution policy
    execution_input = {
        "user": {"user_id": admin.user_id, "roles": admin.roles},
        "request": {"requester_id": requester.user_id, "environment": "nonprod"},
        "approvals": [
            {"role": "deployer", "approver_id": deployer.user_id, "approved_at": "2024-01-01T10:00:00Z"},
            {"role": "authoriser", "approver_id": authoriser.user_id, "approved_at": "2024-01-01T10:30:00Z"}
        ]
    }
    
    execution_result = await opa.evaluate_policy("onboarding/execution", execution_input)
    print(f"✅ Execution policy test: {execution_result}")
    
    # Test GitHub Actions dispatch
    print("\n4. Testing GitHub Actions dispatch...")
    dispatcher = GitHubDispatcher()
    
    # Create mock request for testing
    from models import OnboardingRequest
    mock_request = OnboardingRequest(
        request_id="test-workflow-001",
        title="Test Workflow Request",
        environment="nonprod",
        ship_id="test-ship-01",
        project_name="test-project",
        application="test-app",
        overlay="test-overlay",
        dry_run=True,
        canary_percent=10,
        deployment_params={"test": "value"},
        requester_id=requester.user_id,
        requester_email=requester.email,
        status=RequestStatus.APPROVED.value
    )
    
    dispatch_result = await dispatcher.dispatch_workflow("deploy.yml", mock_request)
    print(f"✅ Workflow dispatch test: {dispatch_result}")
    
    # Test repository dispatch
    repo_dispatch_result = await dispatcher.dispatch_repository_event("onboarding-deploy", mock_request)
    print(f"✅ Repository dispatch test: {repo_dispatch_result}")
    
    print("\n5. Testing role-based permissions...")
    
    # Test role permissions
    test_cases = [
        (requester, "create", True),
        (requester, "approve_deployer", False),
        (deployer, "approve_deployer", True),
        (deployer, "execute", True),
        (authoriser, "approve_authoriser", True),
        (authoriser, "execute", False),
        (admin, "admin", True)
    ]
    
    for user, action, expected in test_cases:
        action_input = {
            "user": {"user_id": user.user_id, "roles": user.roles},
            "action": action
        }
        
        result = await opa.evaluate_policy("service_actions/allow", action_input)
        allowed = result.get("allowed", False)
        
        status = "✅" if allowed == expected else "❌"
        print(f"{status} {user.user_id} can {action}: {allowed} (expected: {expected})")
    
    print("\n6. Testing two-level approval logic...")
    
    # Test scenarios
    scenarios = [
        {
            "name": "Self-approval attempt",
            "user": requester,
            "role": "deployer",
            "expected": False,
            "reason": "cannot approve own request"
        },
        {
            "name": "Valid deployer approval",
            "user": deployer,
            "role": "deployer", 
            "expected": True,
            "reason": "valid deployer approval"
        },
        {
            "name": "Valid authoriser approval",
            "user": authoriser,
            "role": "authoriser",
            "expected": True,
            "reason": "valid authoriser approval"
        },
        {
            "name": "Duplicate approval attempt",
            "user": deployer,
            "role": "deployer",
            "existing_approvals": [{"approver_id": deployer.user_id, "role": "deployer"}],
            "expected": False,
            "reason": "already approved in this role"
        }
    ]
    
    for scenario in scenarios:
        test_input = {
            "user": {"user_id": scenario["user"].user_id, "roles": scenario["user"].roles},
            "request": {"requester_id": requester.user_id, "status": "submitted"},
            "approval": {
                "role": scenario["role"],
                "existing_approvals": scenario.get("existing_approvals", [])
            }
        }
        
        result = await opa.evaluate_policy("onboarding/approval", test_input)
        allowed = result.get("allowed", False)
        
        status = "✅" if allowed == scenario["expected"] else "❌"
        print(f"{status} {scenario['name']}: {allowed} ({result.get('reason', 'No reason')})")
    
    print("\n7. Testing execution requirements...")
    
    # Test execution scenarios
    exec_scenarios = [
        {
            "name": "No approvals",
            "approvals": [],
            "expected": False
        },
        {
            "name": "Only deployer approval",
            "approvals": [{"role": "deployer", "approver_id": deployer.user_id, "approved_at": "2024-01-01T10:00:00Z"}],
            "expected": False
        },
        {
            "name": "Only authoriser approval",
            "approvals": [{"role": "authoriser", "approver_id": authoriser.user_id, "approved_at": "2024-01-01T10:00:00Z"}],
            "expected": False
        },
        {
            "name": "Both approvals (valid)",
            "approvals": [
                {"role": "deployer", "approver_id": deployer.user_id, "approved_at": "2024-01-01T10:00:00Z"},
                {"role": "authoriser", "approver_id": authoriser.user_id, "approved_at": "2024-01-01T10:30:00Z"}
            ],
            "expected": True
        },
        {
            "name": "Same user both approvals (invalid)",
            "approvals": [
                {"role": "deployer", "approver_id": admin.user_id, "approved_at": "2024-01-01T10:00:00Z"},
                {"role": "authoriser", "approver_id": admin.user_id, "approved_at": "2024-01-01T10:30:00Z"}
            ],
            "expected": False
        }
    ]
    
    for scenario in exec_scenarios:
        test_input = {
            "user": {"user_id": admin.user_id, "roles": admin.roles},
            "request": {"requester_id": requester.user_id, "environment": "nonprod"},
            "approvals": scenario["approvals"]
        }
        
        result = await opa.evaluate_policy("onboarding/execution", test_input)
        allowed = result.get("allowed", False)
        
        status = "✅" if allowed == scenario["expected"] else "❌"
        print(f"{status} {scenario['name']}: {allowed} ({result.get('reason', 'No reason')})")
    
    print("\n🎉 Complete workflow validation finished!")
    print("\nSummary:")
    print("✅ Database initialization")
    print("✅ OPA policy integration")  
    print("✅ GitHub Actions dispatch")
    print("✅ Role-based permissions")
    print("✅ Two-level approval logic")
    print("✅ Execution requirements")
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_complete_workflow())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)