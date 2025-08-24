# AIOps Onboarding Service

A secure FastAPI-based service for ship and project onboarding with two-level approval workflows, OIDC authentication, and OPA policy enforcement.

## Features

- **Secure Authentication**: OIDC integration with Keycloak for user authentication
- **Role-Based Access Control**: Five role levels (requester, deployer, authoriser, admin, viewer)
- **Two-Level Approval Workflow**: Requires approval from both deployer and authoriser roles
- **Policy Enforcement**: OPA integration for authorization decisions
- **GitHub Actions Integration**: Automated deployment triggering via workflow dispatch
- **Audit Logging**: Complete audit trail with CSV/JSON export
- **Web UI**: Jinja2-based templates for request management
- **REST API**: Complete CRUD operations for programmatic access

## Architecture

```
User Request → OIDC Auth → Role Check → OPA Policy → Two-Level Approval → GitHub Actions Dispatch
                                     ↓
                             Audit Log → Notifications
```

## User Roles

- **Requester**: Can create and submit onboarding requests
- **Deployer**: Can provide deployer-level approvals and execute deployments
- **Authoriser**: Can provide authoriser-level approvals
- **Admin**: Full access to all operations
- **Viewer**: Read-only access to requests and audit logs

## Approval Workflow

1. **Request Creation**: User creates onboarding request (draft status)
2. **Submission**: User submits request for approval (submitted status)
3. **Deployer Approval**: Deployer reviews and approves/rejects
4. **Authoriser Approval**: Authoriser reviews and approves/rejects
5. **Policy Check**: OPA validates two-level approval requirements
6. **Execution**: Authorized user executes deployment via GitHub Actions

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///./onboarding.db

# OIDC Configuration
OIDC_ISSUER_URL=http://keycloak:8080/realms/aiops
OIDC_CLIENT_ID=onboarding-service
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=http://localhost:8090/auth/callback

# Security
SECRET_KEY=your-secret-key

# Feature Flags
DEPLOY_DRY_RUN=true
POLICY_MODE=enforcing
USE_MOCK_ACTIONS=false
CANARY_PERCENT=10

# External Services
OPA_URL=http://opa:8181
GITHUB_TOKEN=your-github-token
GITHUB_REPO_OWNER=iLodeStar
GITHUB_REPO_NAME=AIOps-NAAS

# Notifications
WEBHOOK_URL=https://your-webhook-endpoint
SMTP_HOST=smtp.example.com
SMTP_USER=notifications@cruise.com
SMTP_PASSWORD=your-smtp-password
```

## Installation & Setup

### Local Development

1. **Install Dependencies**:
   ```bash
   cd services/onboarding-service
   pip install -r requirements.txt
   ```

2. **Initialize Database**:
   ```bash
   python -c "from db import init_db; init_db()"
   ```

3. **Run Service**:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8090 --reload
   ```

4. **Access UI**: http://localhost:8090

### Docker Deployment

```bash
# Build image
docker build -t onboarding-service .

# Run container
docker run -d -p 8090:8090 \
  -e DATABASE_URL=sqlite:///./data/onboarding.db \
  -e OIDC_ISSUER_URL=http://keycloak:8080/realms/aiops \
  -e SECRET_KEY=your-secret-key \
  -v $(pwd)/data:/app/data \
  onboarding-service
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: onboarding-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: onboarding-service
  template:
    metadata:
      labels:
        app: onboarding-service
    spec:
      containers:
      - name: onboarding-service
        image: onboarding-service:latest
        ports:
        - containerPort: 8090
        env:
        - name: DATABASE_URL
          value: "postgresql://user:pass@postgres:5432/onboarding"
        - name: OIDC_ISSUER_URL
          value: "http://keycloak:8080/realms/aiops"
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: onboarding-secrets
              key: secret-key
---
apiVersion: v1
kind: Service
metadata:
  name: onboarding-service
spec:
  selector:
    app: onboarding-service
  ports:
  - port: 8090
    targetPort: 8090
```

## API Endpoints

### Authentication
- `GET /auth/login` - Initiate OIDC login
- `GET /auth/callback` - Handle OIDC callback
- `GET /auth/logout` - Logout and clear session

### Web UI
- `GET /` - Dashboard
- `GET /requests` - List requests (with pagination/filters)
- `GET /requests/new` - New request form
- `GET /requests/{id}` - Request details

### REST API
- `GET /health` - Health check
- `POST /api/requests` - Create request
- `GET /api/requests` - List requests
- `GET /api/requests/{id}` - Get request
- `POST /api/requests/{id}/submit` - Submit for approval
- `POST /api/requests/{id}/approve` - Approve/reject request
- `POST /api/requests/{id}/execute` - Execute deployment
- `GET /api/requests/{id}/approvals` - Get approvals
- `GET /api/audit/{id}` - Get audit log (JSON/CSV)

## Testing

### Unit Tests
```bash
python -m pytest tests/test_onboarding.py -v
```

### Integration Tests
```bash
# Test components
python tests/test_integration.py

# Test against running server
python tests/test_integration.py server
```

### Manual Testing

1. **Start Service**: `uvicorn app:app --reload`
2. **Create Request**: POST to `/api/requests` with test data
3. **Submit Request**: POST to `/api/requests/{id}/submit`
4. **Approve as Deployer**: POST to `/api/requests/{id}/approve` with `role: deployer`
5. **Approve as Authoriser**: POST to `/api/requests/{id}/approve` with `role: authoriser`
6. **Execute**: POST to `/api/requests/{id}/execute`
7. **Check Audit**: GET `/api/audit/{id}`

## OPA Policies

The service includes comprehensive OPA policies for:

- **Two-Level Approval Enforcement**: Requires distinct deployer and authoriser approvals
- **Role-Based Access Control**: Validates user permissions for actions
- **Environment-Specific Rules**: Stricter policies for production deployments
- **Self-Approval Prevention**: Users cannot approve their own requests

### Policy Files
- `opa/policies/onboarding.rego` - Main onboarding approval policies
- `opa/policies/service-actions.rego` - General service action policies

## GitHub Actions Integration

The service can trigger GitHub Actions workflows for deployment:

- **Workflow Dispatch**: Triggers specific workflow with parameters
- **Repository Dispatch**: Sends custom events for flexible automation
- **Parameter Passing**: Includes request details, environment, and execution context

### Example Workflow Trigger

```yaml
name: Deploy Ship Configuration
on:
  workflow_dispatch:
    inputs:
      request_id:
        description: 'Onboarding request ID'
        required: true
      environment:
        description: 'Deployment environment'
        required: true
      ship_id:
        description: 'Ship identifier'
        required: true
      dry_run:
        description: 'Dry run mode'
        required: true
        default: 'true'
```

## Security Considerations

- **OIDC Authentication**: Secure token-based authentication
- **Session Management**: Secure session cookies with HMAC signing
- **Role Mapping**: Flexible mapping from OIDC groups to application roles
- **Policy Enforcement**: All actions validated through OPA policies
- **Audit Trail**: Complete logging of all state changes
- **Input Validation**: Comprehensive validation of all user inputs

## Production Deployment

For production deployment:

1. **Use PostgreSQL**: Set `DATABASE_URL` to PostgreSQL connection string
2. **Configure OIDC**: Set up Keycloak realm and client
3. **Set Secrets**: Use secure secret management for keys and tokens
4. **Enable HTTPS**: Configure TLS termination
5. **Monitor**: Set up logging and monitoring integration
6. **Backup**: Configure database backup strategy

## Troubleshooting

### Common Issues

1. **OIDC Login Fails**: Check Keycloak configuration and client settings
2. **Approval Blocked**: Verify user roles and OPA policy configuration
3. **Execution Fails**: Check GitHub token permissions and workflow configuration
4. **Database Errors**: Verify database connection and permissions

### Logs

The service provides structured logging for debugging:

```bash
# View logs
docker logs onboarding-service

# Follow logs
docker logs -f onboarding-service
```

## Development

### Code Structure

```
services/onboarding-service/
├── app.py                 # Main FastAPI application
├── auth.py               # OIDC authentication
├── models.py             # SQLAlchemy models
├── db.py                 # Database session management
├── opa_client.py         # OPA integration
├── github_dispatch.py    # GitHub Actions integration
├── config.py             # Configuration management
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container build
├── templates/           # Jinja2 UI templates
├── static/             # CSS/JS assets
├── tests/              # Unit and integration tests
└── alembic/            # Database migrations
```

### Contributing

1. Follow existing code patterns from other services
2. Add tests for new functionality
3. Update documentation for changes
4. Ensure OPA policies are comprehensive
5. Test approval workflows thoroughly

## License

This service is part of the AIOps NAAS platform and follows the same licensing as the parent project.