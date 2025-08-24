"""OIDC authentication and session management."""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import base64
import hmac
import hashlib

from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from config import settings
from models import User, UserRole
from db import get_db

logger = logging.getLogger(__name__)

# Simple session serializer without itsdangerous
class SimpleSessionSerializer:
    """Simple session serialization using HMAC."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()
    
    def dumps(self, data: dict) -> str:
        """Serialize data to signed string."""
        payload = json.dumps(data).encode()
        payload_b64 = base64.b64encode(payload).decode()
        signature = hmac.new(self.secret_key, payload_b64.encode(), hashlib.sha256).hexdigest()
        return f"{payload_b64}.{signature}"
    
    def loads(self, token: str, max_age: int = 86400) -> dict:
        """Deserialize and verify signed string."""
        try:
            payload_b64, signature = token.split('.', 1)
            expected_signature = hmac.new(self.secret_key, payload_b64.encode(), hashlib.sha256).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                raise ValueError("Invalid signature")
            
            payload = base64.b64decode(payload_b64).decode()
            data = json.loads(payload)
            
            # Check expiration
            created_at = datetime.fromisoformat(data.get('created_at', ''))
            if (datetime.now(timezone.utc) - created_at).total_seconds() > max_age:
                raise ValueError("Token expired")
            
            return data
        except (ValueError, json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Token verification failed: {e}")

# Session serializer for secure cookies
serializer = SimpleSessionSerializer(settings.secret_key)

# Mock OAuth for development (since authlib might not be available)
class MockOAuth:
    """Mock OAuth for development."""
    def register(self, **kwargs):
        pass
    
    @property
    def keycloak(self):
        return self
    
    async def authorize_redirect(self, redirect_uri):
        # In development, redirect to callback with mock token
        return RedirectResponse(url="/auth/callback?code=mock_code")
    
    async def authorize_access_token(self, request):
        # Return mock token
        return {
            'userinfo': {
                'sub': 'dev_user',
                'email': 'dev@cruise.com',
                'name': 'Dev User',
                'preferred_username': 'dev_user'
            },
            'realm_access': {
                'roles': ['aiops-admin']
            }
        }

oauth = MockOAuth()

def init_oauth():
    """Initialize OAuth client."""
    pass  # Mock implementation


class UserInfo:
    """User information from OIDC token."""
    
    def __init__(self, user_id: str, email: str, name: str, roles: List[str]):
        self.user_id = user_id
        self.email = email
        self.name = name
        self.roles = roles
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has specific role."""
        return role.value in self.roles
    
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.has_role(UserRole.ADMIN)
    
    def can_approve_as_deployer(self) -> bool:
        """Check if user can approve as deployer."""
        return self.has_role(UserRole.DEPLOYER) or self.has_role(UserRole.ADMIN)
    
    def can_approve_as_authoriser(self) -> bool:
        """Check if user can approve as authoriser."""
        return self.has_role(UserRole.AUTHORISER) or self.has_role(UserRole.ADMIN)
    
    def can_execute_deployment(self) -> bool:
        """Check if user can execute deployments."""
        return self.has_role(UserRole.ADMIN) or self.has_role(UserRole.DEPLOYER)


def create_session_token(user_info: UserInfo) -> str:
    """Create a secure session token."""
    data = {
        'user_id': user_info.user_id,
        'email': user_info.email,
        'name': user_info.name,
        'roles': user_info.roles,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    return serializer.dumps(data)


def verify_session_token(token: str) -> Optional[UserInfo]:
    """Verify and decode session token."""
    try:
        # Token valid for 24 hours
        data = serializer.loads(token, max_age=86400)
        return UserInfo(
            user_id=data['user_id'],
            email=data['email'],
            name=data['name'],
            roles=data['roles']
        )
    except (ValueError, KeyError):
        return None


def get_session_from_request(request: Request) -> Optional[UserInfo]:
    """Extract user session from request."""
    # Check session cookie
    session_token = request.cookies.get('session')
    if session_token:
        return verify_session_token(session_token)
    
    # Check Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header[7:]
        return verify_session_token(token)
    
    return None


def extract_roles_from_token(token: Dict[str, Any]) -> List[str]:
    """Extract roles from OIDC token."""
    roles = []
    
    # Check realm roles
    if 'realm_access' in token and 'roles' in token['realm_access']:
        roles.extend(token['realm_access']['roles'])
    
    # Check resource roles (for client-specific roles)
    if 'resource_access' in token:
        client_roles = token['resource_access'].get(settings.oidc_client_id, {})
        if 'roles' in client_roles:
            roles.extend(client_roles['roles'])
    
    # Map common roles to our role system
    role_mapping = {
        'aiops-requester': UserRole.REQUESTER.value,
        'aiops-deployer': UserRole.DEPLOYER.value,
        'aiops-authoriser': UserRole.AUTHORISER.value,
        'aiops-admin': UserRole.ADMIN.value,
        'aiops-viewer': UserRole.VIEWER.value,
    }
    
    mapped_roles = []
    for role in roles:
        if role in role_mapping:
            mapped_roles.append(role_mapping[role])
        elif role in [r.value for r in UserRole]:
            mapped_roles.append(role)
    
    # Default to viewer if no specific roles found
    if not mapped_roles:
        mapped_roles = [UserRole.VIEWER.value]
    
    return list(set(mapped_roles))


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> UserInfo:
    """Dependency to get current authenticated user."""
    user_info = get_session_from_request(request)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Update user in database
    user = db.query(User).filter(User.user_id == user_info.user_id).first()
    if user:
        user.last_login = datetime.now(timezone.utc)
        user.roles = user_info.roles
        db.commit()
    else:
        # Create new user record
        user = User(
            user_id=user_info.user_id,
            email=user_info.email,
            name=user_info.name,
            roles=user_info.roles,
            last_login=datetime.now(timezone.utc)
        )
        db.add(user)
        db.commit()
    
    return user_info


def require_role(required_role: UserRole):
    """Dependency to require specific role."""
    async def check_role(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if not user.has_role(required_role) and not user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value}"
            )
        return user
    return check_role


def require_any_role(required_roles: List[UserRole]):
    """Dependency to require any of the specified roles."""
    async def check_roles(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if not any(user.has_role(role) for role in required_roles) and not user.is_admin():
            role_names = [role.value for role in required_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(role_names)}"
            )
        return user
    return check_roles


# For testing - mock authentication
class MockUserInfo(UserInfo):
    """Mock user info for testing."""
    
    def __init__(self, user_id: str = "test_user", email: str = "test@cruise.com", 
                 name: str = "Test User", roles: List[str] = None):
        if roles is None:
            roles = [UserRole.ADMIN.value]
        super().__init__(user_id, email, name, roles)


def get_mock_user() -> UserInfo:
    """Get mock user for testing."""
    return MockUserInfo()


def create_test_token(user_id: str, roles: List[str]) -> str:
    """Create test token for integration tests."""
    user_info = UserInfo(
        user_id=user_id,
        email=f"{user_id}@cruise.com",
        name=f"Test {user_id}",
        roles=roles
    )
    return create_session_token(user_info)