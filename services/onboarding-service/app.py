"""Main FastAPI application for onboarding service."""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import json
import csv
import io

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status, Form, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_

from config import settings
from models import OnboardingRequest, Approval, AuditLog, RequestStatus, UserRole
from db import get_db, init_db
from auth import (
    get_current_user, require_role, require_any_role, UserInfo, 
    oauth, init_oauth, create_session_token, extract_roles_from_token
)
from opa_client import opa_client
from github_dispatch import github_dispatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AIOps Onboarding Service",
    description="Secure ship/project onboarding with two-level approvals",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
import os

# Mock template renderer for development
class MockTemplates:
    """Mock template renderer."""
    def __init__(self, directory):
        self.directory = directory
    
    def TemplateResponse(self, template_name, context):
        """Return mock HTML response."""
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head><title>Onboarding Service - {template_name}</title></head>
        <body>
            <h1>Onboarding Service</h1>
            <p>Template: {template_name}</p>
            <p>User: {context.get('user', {}).get('email', 'Anonymous')}</p>
            <p>Context keys: {list(context.keys())}</p>
        </body>
        </html>
        """)

template_dir = os.path.join(os.path.dirname(__file__), "templates")
static_dir = os.path.join(os.path.dirname(__file__), "static")
templates = MockTemplates(template_dir)

# Mock static files
try:
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
except ImportError:
    # Skip static files if not available
    pass

# Initialize OAuth and database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    try:
        init_oauth()
        init_db()
        logger.info("Onboarding service started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise


# Pydantic models for API
class OnboardingRequestCreate(BaseModel):
    """Model for creating onboarding requests."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    ship_id: Optional[str] = Field(None, max_length=50)
    project_name: Optional[str] = Field(None, max_length=100)
    environment: str = Field(default="nonprod", pattern="^(nonprod|prod)$")
    application: Optional[str] = Field(None, max_length=100)
    overlay: Optional[str] = Field(None, max_length=50)
    deployment_params: Optional[Dict[str, Any]] = Field(default_factory=dict)
    dry_run: bool = True
    canary_percent: int = Field(default=10, ge=0, le=100)


class OnboardingRequestUpdate(BaseModel):
    """Model for updating onboarding requests."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    ship_id: Optional[str] = Field(None, max_length=50)
    project_name: Optional[str] = Field(None, max_length=100)
    environment: Optional[str] = Field(None, pattern="^(nonprod|prod)$")
    application: Optional[str] = Field(None, max_length=100)
    overlay: Optional[str] = Field(None, max_length=50)
    deployment_params: Optional[Dict[str, Any]] = None
    dry_run: Optional[bool] = None
    canary_percent: Optional[int] = Field(None, ge=0, le=100)


class ApprovalCreate(BaseModel):
    """Model for creating approvals."""
    role: str = Field(..., pattern="^(deployer|authoriser)$")
    decision: str = Field(..., pattern="^(approved|rejected)$")
    comments: Optional[str] = None


class OnboardingRequestResponse(BaseModel):
    """Response model for onboarding requests."""
    id: int
    request_id: str
    title: str
    description: Optional[str]
    ship_id: Optional[str]
    project_name: Optional[str]
    environment: str
    application: Optional[str]
    overlay: Optional[str]
    deployment_params: Dict[str, Any]
    dry_run: bool
    canary_percent: int
    status: str
    requester_id: str
    requester_email: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    submitted_at: Optional[datetime]
    executed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ApprovalResponse(BaseModel):
    """Response model for approvals."""
    id: int
    role: str
    approver_id: str
    approver_email: Optional[str]
    decision: str
    comments: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Utility functions
async def log_audit_event(
    db: Session,
    request_id: str,
    action: str,
    user: UserInfo,
    old_status: Optional[str] = None,
    new_status: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """Log audit event."""
    audit_log = AuditLog(
        request_id=request_id,
        action=action,
        user_id=user.user_id,
        user_email=user.email,
        user_roles=user.roles,
        old_status=old_status,
        new_status=new_status,
        details=details or {}
    )
    db.add(audit_log)
    db.commit()


async def send_notification(
    action: str,
    request: OnboardingRequest,
    user: UserInfo,
    additional_context: Optional[Dict[str, Any]] = None
):
    """Send notification (webhook or email stub)."""
    notification_data = {
        "action": action,
        "request_id": request.request_id,
        "title": request.title,
        "environment": request.environment,
        "requester": {
            "user_id": request.requester_id,
            "email": request.requester_email
        },
        "actor": {
            "user_id": user.user_id,
            "email": user.email,
            "roles": user.roles
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "additional_context": additional_context or {}
    }
    
    # Log notification (webhook/email stub)
    logger.info(f"NOTIFICATION: {action} for request {request.request_id}")
    logger.info(f"Notification data: {json.dumps(notification_data, indent=2)}")
    
    # TODO: Implement actual webhook/email sending here
    # if settings.webhook_url:
    #     await send_webhook(settings.webhook_url, notification_data)
    # if settings.smtp_host:
    #     await send_email(notification_data)


# UI Routes (Templates)
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: UserInfo = Depends(get_current_user)):
    """Home page."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "can_create": user.has_role(UserRole.REQUESTER) or user.is_admin()
    })


@app.get("/auth/login")
async def login():
    """Initiate OIDC login."""
    redirect_uri = settings.oidc_redirect_uri
    return await oauth.keycloak.authorize_redirect(redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """Handle OIDC callback."""
    try:
        token = await oauth.keycloak.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info from OIDC provider")
        
        # Extract user details and roles
        user_id = user_info.get('sub') or user_info.get('preferred_username')
        email = user_info.get('email')
        name = user_info.get('name') or user_info.get('preferred_username')
        roles = extract_roles_from_token(token)
        
        # Create user info object
        auth_user = UserInfo(user_id=user_id, email=email, name=name, roles=roles)
        
        # Create session token
        session_token = create_session_token(auth_user)
        
        # Log audit event
        await log_audit_event(
            db=db,
            request_id="system",
            action="login",
            user=auth_user,
            details={"roles": roles}
        )
        
        # Set session cookie and redirect
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key="session",
            value=session_token,
            httponly=True,
            secure=not settings.debug,
            samesite="lax",
            max_age=86400  # 24 hours
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")


@app.get("/auth/logout")
async def logout():
    """Logout and clear session."""
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("session")
    return response


@app.get("/requests/new", response_class=HTMLResponse)
async def new_request_form(
    request: Request,
    user: UserInfo = Depends(require_any_role([UserRole.REQUESTER, UserRole.ADMIN]))
):
    """Show new request form."""
    return templates.TemplateResponse("submit.html", {
        "request": request,
        "user": user
    })


@app.get("/requests", response_class=HTMLResponse)
async def list_requests(
    request: Request,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """List requests with pagination and filtering."""
    page_size = 20
    offset = (page - 1) * page_size
    
    # Build query
    query = db.query(OnboardingRequest)
    
    # Apply filters
    if status_filter and status_filter != "all":
        query = query.filter(OnboardingRequest.status == status_filter)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                OnboardingRequest.title.ilike(search_term),
                OnboardingRequest.description.ilike(search_term),
                OnboardingRequest.ship_id.ilike(search_term),
                OnboardingRequest.project_name.ilike(search_term)
            )
        )
    
    # Apply role-based filtering
    if not user.is_admin():
        if user.has_role(UserRole.VIEWER):
            # Viewers can see all requests
            pass
        else:
            # Others can only see their own requests or requests they can act on
            query = query.filter(OnboardingRequest.requester_id == user.user_id)
    
    # Get total count for pagination
    total_count = query.count()
    
    # Get page of results
    requests = query.order_by(desc(OnboardingRequest.created_at))\
                   .offset(offset)\
                   .limit(page_size)\
                   .all()
    
    # Calculate pagination info
    total_pages = (total_count + page_size - 1) // page_size
    has_prev = page > 1
    has_next = page < total_pages
    
    return templates.TemplateResponse("list.html", {
        "request": request,
        "user": user,
        "requests": requests,
        "page": page,
        "total_pages": total_pages,
        "has_prev": has_prev,
        "has_next": has_next,
        "status_filter": status_filter,
        "search": search,
        "total_count": total_count
    })


@app.get("/requests/{request_id}", response_class=HTMLResponse)
async def view_request(
    request: Request,
    request_id: str,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View request details."""
    onboarding_request = db.query(OnboardingRequest)\
                          .filter(OnboardingRequest.request_id == request_id)\
                          .first()
    
    if not onboarding_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Check permissions
    if not user.is_admin() and not user.has_role(UserRole.VIEWER):
        if onboarding_request.requester_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Get approvals and audit logs
    approvals = db.query(Approval)\
                  .filter(Approval.request_id == request_id)\
                  .order_by(Approval.created_at)\
                  .all()
    
    audit_logs = db.query(AuditLog)\
                   .filter(AuditLog.request_id == request_id)\
                   .order_by(desc(AuditLog.timestamp))\
                   .all()
    
    # Check if user can approve
    can_approve_deployer = False
    can_approve_authoriser = False
    can_execute = False
    
    if onboarding_request.status in [RequestStatus.SUBMITTED.value, RequestStatus.DEPLOYER_APPROVED.value]:
        if user.can_approve_as_deployer():
            # Check with OPA if user can approve as deployer
            opa_result = await opa_client.can_approve_request(
                user, onboarding_request, "deployer", approvals
            )
            can_approve_deployer = opa_result.get("allowed", False)
        
        if user.can_approve_as_authoriser():
            # Check with OPA if user can approve as authoriser
            opa_result = await opa_client.can_approve_request(
                user, onboarding_request, "authoriser", approvals
            )
            can_approve_authoriser = opa_result.get("allowed", False)
    
    # Check if user can execute
    if onboarding_request.status == RequestStatus.APPROVED.value and user.can_execute_deployment():
        opa_result = await opa_client.can_execute_request(user, onboarding_request, approvals)
        can_execute = opa_result.get("allowed", False)
    
    return templates.TemplateResponse("details.html", {
        "request": request,
        "user": user,
        "onboarding_request": onboarding_request,
        "approvals": approvals,
        "audit_logs": audit_logs,
        "can_approve_deployer": can_approve_deployer,
        "can_approve_authoriser": can_approve_authoriser,
        "can_execute": can_execute,
        "RequestStatus": RequestStatus
    })


# API Routes
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "onboarding-service",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/api/requests", response_model=OnboardingRequestResponse)
async def create_request(
    request_data: OnboardingRequestCreate,
    user: UserInfo = Depends(require_any_role([UserRole.REQUESTER, UserRole.ADMIN])),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Create a new onboarding request."""
    
    # Create request
    request_id = str(uuid.uuid4())
    onboarding_request = OnboardingRequest(
        request_id=request_id,
        title=request_data.title,
        description=request_data.description,
        ship_id=request_data.ship_id,
        project_name=request_data.project_name,
        environment=request_data.environment,
        application=request_data.application,
        overlay=request_data.overlay,
        deployment_params=request_data.deployment_params,
        dry_run=request_data.dry_run,
        canary_percent=request_data.canary_percent,
        status=RequestStatus.DRAFT.value,
        requester_id=user.user_id,
        requester_email=user.email
    )
    
    db.add(onboarding_request)
    db.commit()
    db.refresh(onboarding_request)
    
    # Log audit event
    await log_audit_event(
        db=db,
        request_id=request_id,
        action="create",
        user=user,
        new_status=RequestStatus.DRAFT.value,
        details=request_data.model_dump()
    )
    
    return OnboardingRequestResponse.model_validate(onboarding_request)


@app.post("/api/requests/{request_id}/submit")
async def submit_request(
    request_id: str,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Submit request for approval."""
    
    onboarding_request = db.query(OnboardingRequest)\
                          .filter(OnboardingRequest.request_id == request_id)\
                          .first()
    
    if not onboarding_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Check permissions
    if onboarding_request.requester_id != user.user_id and not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")
    
    if onboarding_request.status != RequestStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Request already submitted")
    
    # Update status
    old_status = onboarding_request.status
    onboarding_request.status = RequestStatus.SUBMITTED.value
    onboarding_request.submitted_at = datetime.now(timezone.utc)
    
    db.commit()
    
    # Log audit event
    await log_audit_event(
        db=db,
        request_id=request_id,
        action="submit",
        user=user,
        old_status=old_status,
        new_status=RequestStatus.SUBMITTED.value
    )
    
    # Send notification
    background_tasks.add_task(
        send_notification,
        "submitted",
        onboarding_request,
        user
    )
    
    return {"message": "Request submitted for approval", "status": RequestStatus.SUBMITTED.value}


@app.post("/api/requests/{request_id}/approve")
async def approve_request(
    request_id: str,
    approval_data: ApprovalCreate,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Approve or reject a request."""
    
    onboarding_request = db.query(OnboardingRequest)\
                          .filter(OnboardingRequest.request_id == request_id)\
                          .first()
    
    if not onboarding_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Check if request is in appropriate status
    if onboarding_request.status not in [RequestStatus.SUBMITTED.value, RequestStatus.DEPLOYER_APPROVED.value]:
        raise HTTPException(status_code=400, detail="Request not in approvable state")
    
    # Get existing approvals
    existing_approvals = db.query(Approval)\
                          .filter(Approval.request_id == request_id)\
                          .all()
    
    # Check with OPA if user can approve in this role
    opa_result = await opa_client.can_approve_request(
        user, onboarding_request, approval_data.role, existing_approvals
    )
    
    if not opa_result.get("allowed", False):
        raise HTTPException(
            status_code=403,
            detail=f"Approval denied: {opa_result.get('reason', 'Unknown reason')}"
        )
    
    # Create approval record
    approval = Approval(
        request_id=request_id,
        role=approval_data.role,
        approver_id=user.user_id,
        approver_email=user.email,
        decision=approval_data.decision,
        comments=approval_data.comments
    )
    
    db.add(approval)
    
    # Update request status based on approvals
    old_status = onboarding_request.status
    new_status = old_status
    
    if approval_data.decision == "rejected":
        new_status = RequestStatus.REJECTED.value
    else:  # approved
        # Check what approvals we now have
        all_approvals = existing_approvals + [approval]
        deployer_approved = any(a.role == "deployer" and a.decision == "approved" for a in all_approvals)
        authoriser_approved = any(a.role == "authoriser" and a.decision == "approved" for a in all_approvals)
        
        if deployer_approved and authoriser_approved:
            new_status = RequestStatus.APPROVED.value
        elif deployer_approved:
            new_status = RequestStatus.DEPLOYER_APPROVED.value
        elif authoriser_approved:
            new_status = RequestStatus.AUTHORISER_APPROVED.value if old_status == RequestStatus.SUBMITTED.value else old_status
    
    onboarding_request.status = new_status
    
    db.commit()
    
    # Log audit event
    await log_audit_event(
        db=db,
        request_id=request_id,
        action=f"approve_{approval_data.role}",
        user=user,
        old_status=old_status,
        new_status=new_status,
        details={
            "role": approval_data.role,
            "decision": approval_data.decision,
            "comments": approval_data.comments
        }
    )
    
    # Send notification
    background_tasks.add_task(
        send_notification,
        f"{approval_data.decision}_{approval_data.role}",
        onboarding_request,
        user,
        {"comments": approval_data.comments}
    )
    
    return {
        "message": f"Request {approval_data.decision} by {approval_data.role}",
        "status": new_status
    }


@app.post("/api/requests/{request_id}/execute")
async def execute_request(
    request_id: str,
    user: UserInfo = Depends(require_any_role([UserRole.ADMIN, UserRole.DEPLOYER])),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Execute approved request."""
    
    onboarding_request = db.query(OnboardingRequest)\
                          .filter(OnboardingRequest.request_id == request_id)\
                          .first()
    
    if not onboarding_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if onboarding_request.status != RequestStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail="Request not approved for execution")
    
    # Get approvals for OPA check
    approvals = db.query(Approval)\
                  .filter(Approval.request_id == request_id)\
                  .all()
    
    # Final OPA check before execution
    opa_result = await opa_client.can_execute_request(user, onboarding_request, approvals)
    
    if not opa_result.get("allowed", False):
        raise HTTPException(
            status_code=403,
            detail=f"Execution denied: {opa_result.get('reason', 'Unknown reason')}"
        )
    
    # Dispatch GitHub Actions workflow
    dispatch_result = await github_dispatcher.dispatch_workflow(
        workflow_id="deploy.yml",  # Configurable workflow
        request=onboarding_request,
        inputs={
            "executor_id": user.user_id,
            "executor_email": user.email
        }
    )
    
    # Update request status
    old_status = onboarding_request.status
    if dispatch_result.get("success"):
        new_status = RequestStatus.EXECUTED.value
        onboarding_request.executed_at = datetime.now(timezone.utc)
    else:
        new_status = RequestStatus.FAILED.value
    
    onboarding_request.status = new_status
    db.commit()
    
    # Log audit event
    await log_audit_event(
        db=db,
        request_id=request_id,
        action="execute",
        user=user,
        old_status=old_status,
        new_status=new_status,
        details=dispatch_result
    )
    
    # Send notification
    background_tasks.add_task(
        send_notification,
        "executed",
        onboarding_request,
        user,
        {"dispatch_result": dispatch_result}
    )
    
    return {
        "message": "Request execution initiated",
        "status": new_status,
        "dispatch_result": dispatch_result
    }


@app.get("/api/requests", response_model=List[OnboardingRequestResponse])
async def api_list_requests(
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """API endpoint to list requests."""
    
    query = db.query(OnboardingRequest)
    
    # Apply role-based filtering
    if not user.is_admin() and not user.has_role(UserRole.VIEWER):
        query = query.filter(OnboardingRequest.requester_id == user.user_id)
    
    # Apply filters
    if status:
        query = query.filter(OnboardingRequest.status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                OnboardingRequest.title.ilike(search_term),
                OnboardingRequest.description.ilike(search_term),
                OnboardingRequest.ship_id.ilike(search_term),
                OnboardingRequest.project_name.ilike(search_term)
            )
        )
    
    requests = query.order_by(desc(OnboardingRequest.created_at))\
                   .offset(skip)\
                   .limit(limit)\
                   .all()
    
    return [OnboardingRequestResponse.model_validate(req) for req in requests]


@app.get("/api/requests/{request_id}", response_model=OnboardingRequestResponse)
async def api_get_request(
    request_id: str,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """API endpoint to get a specific request."""
    
    onboarding_request = db.query(OnboardingRequest)\
                          .filter(OnboardingRequest.request_id == request_id)\
                          .first()
    
    if not onboarding_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Check permissions
    if not user.is_admin() and not user.has_role(UserRole.VIEWER):
        if onboarding_request.requester_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return OnboardingRequestResponse.model_validate(onboarding_request)


@app.get("/api/requests/{request_id}/approvals", response_model=List[ApprovalResponse])
async def api_get_approvals(
    request_id: str,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """API endpoint to get request approvals."""
    
    # Check if request exists and user has access
    onboarding_request = db.query(OnboardingRequest)\
                          .filter(OnboardingRequest.request_id == request_id)\
                          .first()
    
    if not onboarding_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if not user.is_admin() and not user.has_role(UserRole.VIEWER):
        if onboarding_request.requester_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    approvals = db.query(Approval)\
                  .filter(Approval.request_id == request_id)\
                  .order_by(Approval.created_at)\
                  .all()
    
    return [ApprovalResponse.model_validate(approval) for approval in approvals]


@app.get("/api/audit/{request_id}")
async def api_get_audit_log(
    request_id: str,
    user: UserInfo = Depends(require_any_role([UserRole.ADMIN, UserRole.VIEWER])),
    db: Session = Depends(get_db),
    format: str = Query("json", pattern="^(json|csv)$")
):
    """API endpoint to get audit log."""
    
    audit_logs = db.query(AuditLog)\
                   .filter(AuditLog.request_id == request_id)\
                   .order_by(desc(AuditLog.timestamp))\
                   .all()
    
    if format == "csv":
        # Return CSV format
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "timestamp", "request_id", "action", "user_id", "user_email", 
            "user_roles", "old_status", "new_status", "details"
        ])
        
        # Write data
        for log in audit_logs:
            writer.writerow([
                log.timestamp.isoformat(),
                log.request_id,
                log.action,
                log.user_id,
                log.user_email,
                json.dumps(log.user_roles),
                log.old_status or "",
                log.new_status or "",
                json.dumps(log.details)
            ])
        
        content = output.getvalue()
        output.close()
        
        return StreamingResponse(
            io.StringIO(content),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_{request_id}.csv"}
        )
    
    else:
        # Return JSON format
        return [
            {
                "timestamp": log.timestamp.isoformat(),
                "request_id": log.request_id,
                "action": log.action,
                "user_id": log.user_id,
                "user_email": log.user_email,
                "user_roles": log.user_roles,
                "old_status": log.old_status,
                "new_status": log.new_status,
                "details": log.details
            }
            for log in audit_logs
        ]


# Form-based endpoints for UI
@app.post("/requests/create")
async def create_request_form(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    ship_id: str = Form(""),
    project_name: str = Form(""),
    environment: str = Form("nonprod"),
    application: str = Form(""),
    overlay: str = Form(""),
    dry_run: bool = Form(True),
    canary_percent: int = Form(10),
    user: UserInfo = Depends(require_any_role([UserRole.REQUESTER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Create request via form submission."""
    
    # Create request using API logic
    request_data = OnboardingRequestCreate(
        title=title,
        description=description or None,
        ship_id=ship_id or None,
        project_name=project_name or None,
        environment=environment,
        application=application or None,
        overlay=overlay or None,
        deployment_params={},
        dry_run=dry_run,
        canary_percent=canary_percent
    )
    
    # Use the API endpoint logic
    response = await create_request(request_data, user, db, BackgroundTasks())
    
    # Redirect to the created request
    return RedirectResponse(
        url=f"/requests/{response.request_id}",
        status_code=302
    )


@app.post("/requests/{request_id}/approve")
async def approve_request_form(
    request_id: str,
    role: str = Form(...),
    decision: str = Form(...),
    comments: str = Form(""),
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve request via form submission."""
    
    approval_data = ApprovalCreate(
        role=role,
        decision=decision,
        comments=comments or None
    )
    
    # Use the API endpoint logic
    await approve_request(request_id, approval_data, user, db, BackgroundTasks())
    
    # Redirect back to request details
    return RedirectResponse(
        url=f"/requests/{request_id}",
        status_code=302
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user: UserInfo = Depends(require_any_role([UserRole.ADMIN, UserRole.VIEWER])),
    db: Session = Depends(get_db)
):
    """Admin dashboard."""
    
    # Get statistics
    total_requests = db.query(OnboardingRequest).count()
    pending_requests = db.query(OnboardingRequest)\
                        .filter(OnboardingRequest.status.in_([
                            RequestStatus.SUBMITTED.value,
                            RequestStatus.DEPLOYER_APPROVED.value,
                            RequestStatus.AUTHORISER_APPROVED.value
                        ])).count()
    executed_requests = db.query(OnboardingRequest)\
                         .filter(OnboardingRequest.status == RequestStatus.EXECUTED.value)\
                         .count()
    failed_requests = db.query(OnboardingRequest)\
                       .filter(OnboardingRequest.status.in_([
                           RequestStatus.REJECTED.value,
                           RequestStatus.FAILED.value
                       ])).count()
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": user,
        "total_requests": total_requests,
        "pending_requests": pending_requests,
        "executed_requests": executed_requests,
        "failed_requests": failed_requests,
        "debug": settings.debug,
        "policy_mode": settings.policy_mode,
        "deploy_dry_run": settings.deploy_dry_run,
        "use_mock_actions": settings.use_mock_actions,
        "database_type": "SQLite" if "sqlite" in settings.database_url else "PostgreSQL",
        "opa_url": settings.opa_url
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)