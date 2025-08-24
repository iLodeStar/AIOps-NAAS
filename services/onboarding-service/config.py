"""Configuration management for onboarding service."""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = Field(
        default="sqlite:///./onboarding.db",
        description="Database connection URL"
    )
    
    # OIDC Configuration
    oidc_issuer_url: str = Field(
        default="http://keycloak:8080/realms/aiops",
        description="OIDC issuer URL"
    )
    oidc_client_id: str = Field(
        default="onboarding-service",
        description="OIDC client ID"
    )
    oidc_client_secret: str = Field(
        default="",
        description="OIDC client secret"
    )
    oidc_redirect_uri: str = Field(
        default="http://localhost:8090/auth/callback",
        description="OIDC redirect URI"
    )
    
    # Application
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for session management"
    )
    debug: bool = Field(default=False, description="Debug mode")
    
    # Feature flags
    deploy_dry_run: bool = Field(default=True, description="Default to dry-run deployments")
    policy_mode: str = Field(default="enforcing", description="Policy mode: permissive or enforcing")
    use_mock_actions: bool = Field(default=False, description="Use mock GitHub Actions")
    canary_percent: int = Field(default=10, description="Canary deployment percentage")
    
    # External services
    opa_url: str = Field(default="http://opa:8181", description="OPA server URL")
    github_token: str = Field(default="", description="GitHub token for Actions dispatch")
    github_repo_owner: str = Field(default="iLodeStar", description="GitHub repository owner")
    github_repo_name: str = Field(default="AIOps-NAAS", description="GitHub repository name")
    
    # Notifications
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for notifications")
    smtp_host: Optional[str] = Field(default=None, description="SMTP host for email notifications")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_user: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    notification_from_email: str = Field(
        default="aiops-onboarding@cruise.com",
        description="From email address for notifications"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()