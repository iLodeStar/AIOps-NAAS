# AIOps Onboarding Service - Production Deployment Guide

## Overview

This guide covers deploying the AIOps Onboarding Service to production with full security, monitoring, and compliance features.

## Prerequisites

- Kubernetes cluster (k3s/k8s) with Argo CD
- Keycloak instance configured with AIOps realm  
- PostgreSQL database for production persistence
- OPA (Open Policy Agent) deployment
- GitHub repository with appropriate tokens
- SSL certificates for HTTPS

## Key Features in Production

- **Two-Level Approval Workflow**: Enforced via OPA policies
- **OIDC Authentication**: Keycloak integration with role mapping
- **GitHub Actions Integration**: Automated deployment triggering
- **Comprehensive Audit Logging**: Full compliance trail
- **Policy Enforcement**: OPA-based authorization decisions

## Quick Production Setup

### 1. Database Configuration

```bash
# PostgreSQL setup
export DATABASE_URL="postgresql://user:pass@postgres:5432/aiops_onboarding"
```

### 2. OIDC Configuration  

```bash
# Keycloak realm setup
export OIDC_ISSUER_URL="https://keycloak.yourdomain.com/realms/aiops"
export OIDC_CLIENT_ID="onboarding-service"
export OIDC_CLIENT_SECRET="your-secure-client-secret"
```

### 3. Deploy Service

```bash
# Build and deploy
docker build -t onboarding-service:v1.0.0 services/onboarding-service/
kubectl apply -f k8s/onboarding-service.yaml
```

### 4. Verify Deployment

```bash
# Check service health
curl -f https://onboarding.yourdomain.com/health

# Test authentication flow
# 1. Navigate to https://onboarding.yourdomain.com
# 2. Click login - should redirect to Keycloak
# 3. Login with credentials - should return to dashboard
# 4. Verify roles are displayed correctly
```

## Two-Level Approval Workflow

### Workflow Overview

```
Request Created → Submitted → Deployer Approval → Authoriser Approval → Execution
                     ↓              ↓                    ↓               ↓
                  OPA Check     OPA Check          OPA Check      GitHub Actions
```

### Policy Enforcement

The service enforces:
- **Distinct Approvers**: Deployer and authoriser must be different users
- **Role Validation**: Users must have appropriate roles
- **Self-Approval Prevention**: Users cannot approve their own requests
- **Time Limits**: Production requests have 24-hour approval windows
- **Environment Rules**: Stricter policies for production deployments

### User Roles

- **requester**: Create and submit requests
- **deployer**: Provide technical approvals, execute deployments
- **authoriser**: Provide business/operational approvals
- **admin**: Full access to all operations
- **viewer**: Read-only access for auditing

## Monitoring & Compliance

### Key Metrics

- Request processing time
- Approval workflow completion rate
- Authentication success/failure rates
- Policy evaluation performance
- GitHub Actions execution success

### Audit Requirements

- All state changes logged with user identification
- Export capabilities for compliance reporting
- 7-year retention for maritime regulations
- Tamper-evident audit trail

## Security Features

- **HTTPS Enforcement**: All communications encrypted
- **Session Security**: Secure session management with HMAC
- **Role-Based Access**: Fine-grained permission control
- **Policy Validation**: OPA enforcement for all actions
- **Input Validation**: Comprehensive request validation

For detailed setup instructions, see the complete [Production Deployment Guide](production.md).