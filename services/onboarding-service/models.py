"""Database models for onboarding service."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class RequestStatus(str, Enum):
    """Request status enumeration."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    DEPLOYER_APPROVED = "deployer_approved"
    AUTHORISER_APPROVED = "authoriser_approved"
    APPROVED = "approved"  # Both approvals received
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class UserRole(str, Enum):
    """User role enumeration."""
    REQUESTER = "requester"
    DEPLOYER = "deployer"
    AUTHORISER = "authoriser"
    ADMIN = "admin"
    VIEWER = "viewer"


class OnboardingRequest(Base):
    """Onboarding request model."""
    
    __tablename__ = "onboarding_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(36), unique=True, index=True, nullable=False)
    
    # Request details
    title = Column(String(255), nullable=False)
    description = Column(Text)
    ship_id = Column(String(50))
    project_name = Column(String(100))
    environment = Column(String(20), default="nonprod")  # nonprod, prod
    application = Column(String(100))
    overlay = Column(String(50))
    
    # Deployment parameters
    deployment_params = Column(JSON, default=dict)
    dry_run = Column(Boolean, default=True)
    canary_percent = Column(Integer, default=10)
    
    # Status and workflow
    status = Column(String(20), default=RequestStatus.DRAFT.value)
    requester_id = Column(String(100), nullable=False)
    requester_email = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    submitted_at = Column(DateTime(timezone=True))
    executed_at = Column(DateTime(timezone=True))
    
    # Relationships
    approvals = relationship("Approval", back_populates="request", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="request", cascade="all, delete-orphan")


class Approval(Base):
    """Approval model for two-level approval workflow."""
    
    __tablename__ = "approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(36), ForeignKey("onboarding_requests.request_id"), nullable=False)
    
    # Approval details
    role = Column(String(20), nullable=False)  # deployer, authoriser
    approver_id = Column(String(100), nullable=False)
    approver_email = Column(String(255))
    decision = Column(String(10), nullable=False)  # approved, rejected
    comments = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    request = relationship("OnboardingRequest", back_populates="approvals")


class AuditLog(Base):
    """Audit log for tracking all state changes."""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(36), ForeignKey("onboarding_requests.request_id"), nullable=False)
    
    # Audit details
    action = Column(String(50), nullable=False)
    user_id = Column(String(100), nullable=False)
    user_email = Column(String(255))
    user_roles = Column(JSON, default=list)
    
    # Change tracking
    old_status = Column(String(20))
    new_status = Column(String(20))
    details = Column(JSON, default=dict)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    request = relationship("OnboardingRequest", back_populates="audit_logs")


class User(Base):
    """User model for caching OIDC user information."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255))
    roles = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))