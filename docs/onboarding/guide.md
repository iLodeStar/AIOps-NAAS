# Onboarding Service User Guide

## Overview

The AIOps Onboarding Service provides a secure web interface and API for managing ship and project onboarding requests with a two-level approval workflow.

## Getting Started

### 1. Access the Service

Navigate to the onboarding service URL (typically http://localhost:8090 in development).

### 2. Authentication

Click "Login" to authenticate via OIDC (Keycloak). You'll be redirected to the Keycloak login page.

### 3. Role Assignment

Your roles are automatically assigned based on your Keycloak group memberships:

- **aiops-requester** → Can create and submit requests
- **aiops-deployer** → Can provide deployer approvals and execute deployments
- **aiops-authoriser** → Can provide authoriser approvals
- **aiops-admin** → Full administrative access
- **aiops-viewer** → Read-only access to all requests

## Creating Onboarding Requests

### Step 1: Create Request

1. Click "New Request" from the dashboard
2. Fill in the request details:
   - **Title**: Descriptive title for the request
   - **Description**: Detailed description of requirements
   - **Ship ID**: Unique identifier for the ship (e.g., atlantic-01)
   - **Project Name**: Name of the deployment project
   - **Environment**: nonprod or prod
   - **Application**: Target application name
   - **Overlay**: Configuration overlay to apply
   - **Canary %**: Percentage for canary deployment (0-100)
   - **Dry Run**: Test mode without actual changes (recommended)

3. Click "Create Request"

### Step 2: Submit for Approval

1. Review your request details
2. Click "Submit" to send for approval
3. The request status changes to "Submitted"

## Approval Process

### Two-Level Approval Requirement

Every request requires approval from TWO distinct roles:

1. **Deployer Approval**: Technical approval for deployment feasibility
2. **Authoriser Approval**: Business/operational approval for execution

### Providing Approvals

If you have deployer or authoriser permissions:

1. Navigate to requests list
2. Filter by "Submitted" status to see pending requests
3. Click "View" on a request
4. Click "Approve as Deployer" or "Approve as Authoriser"
5. Add optional comments
6. Submit your approval

### Approval Rules

- You cannot approve your own requests
- You cannot provide multiple approvals for the same request
- Both deployer AND authoriser approval are required
- Approvers must be distinct users
- Production requests have stricter time limits

## Execution

### When Requests Can Be Executed

A request can be executed when:

- It has both deployer and authoriser approvals
- The approvers are distinct users
- OPA policies allow execution
- The executing user has deployment permissions

### Executing Deployments

1. Navigate to a fully approved request
2. Click "Execute Deployment"
3. Confirm the execution
4. The system triggers a GitHub Actions workflow
5. Status updates to "Executed" or "Failed"

## API Usage

### Authentication

For API access, obtain a session token:

```bash
# Login via web interface first, then extract session cookie
curl -b cookies.txt http://localhost:8090/api/requests
```

### Create Request

```bash
curl -X POST http://localhost:8090/api/requests \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "Ship Atlantic-01 Onboarding",
    "description": "Onboard new ship to fleet monitoring",
    "ship_id": "atlantic-01",
    "project_name": "fleet-onboarding",
    "environment": "nonprod",
    "application": "aiops-monitoring",
    "dry_run": true,
    "canary_percent": 10
  }'
```

### Submit Request

```bash
curl -X POST http://localhost:8090/api/requests/{request_id}/submit \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Approve Request

```bash
curl -X POST http://localhost:8090/api/requests/{request_id}/approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "role": "deployer",
    "decision": "approved",
    "comments": "Technical review complete"
  }'
```

## Security Best Practices

1. **Use HTTPS**: Always deploy with TLS in production
2. **Secure Secrets**: Use proper secret management
3. **Regular Audits**: Review audit logs regularly
4. **Role Management**: Regularly review user role assignments
5. **Policy Updates**: Keep OPA policies up to date