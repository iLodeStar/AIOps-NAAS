# AIOps Onboarding Service - Administrator Guide

## Overview

This guide provides administrative procedures for managing the AIOps Onboarding Service in production.

## Administrative Access

### Login as Administrator

1. Navigate to onboarding service URL
2. Login with admin credentials via OIDC
3. Verify "admin" role is displayed
4. Access admin dashboard at `/admin`

### Admin Dashboard Features

- **System Statistics**: Request counts and status distribution
- **Security Status**: Authentication and policy enforcement status
- **Configuration Overview**: Current system settings
- **Admin Tools**: System management functions

## User Management

### Role Assignments

**In Keycloak:**
1. Navigate to Users → {username} → Role mappings
2. Assign realm roles:
   - `aiops-requester` - For requesters
   - `aiops-deployer` - For technical approvers
   - `aiops-authoriser` - For business approvers  
   - `aiops-admin` - For administrators
   - `aiops-viewer` - For auditors

**Role Hierarchy:**
- Admin: Full access (inherits all roles)
- Deployer: Can approve and execute
- Authoriser: Can approve (business level)
- Requester: Can create and submit
- Viewer: Read-only access

### Bulk User Operations

```bash
# Export user list with roles
curl -H "Authorization: Bearer ADMIN_TOKEN" \
     https://onboarding.yourdomain.com/api/users?format=csv

# Audit user activity
curl -H "Authorization: Bearer ADMIN_TOKEN" \
     https://onboarding.yourdomain.com/api/audit/users?days=30
```

## Request Management

### Monitoring Requests

```bash
# Get all pending requests
curl -H "Authorization: Bearer ADMIN_TOKEN" \
     "https://onboarding.yourdomain.com/api/requests?status=submitted"

# Get requests by environment
curl -H "Authorization: Bearer ADMIN_TOKEN" \
     "https://onboarding.yourdomain.com/api/requests?environment=prod"

# Search requests
curl -H "Authorization: Bearer ADMIN_TOKEN" \
     "https://onboarding.yourdomain.com/api/requests?search=ship-name"
```

### Emergency Actions

**Override Approval (Admin Only):**
```bash
# Emergency approval override (use with caution)
curl -X POST https://onboarding.yourdomain.com/api/requests/{id}/admin-override \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Emergency deployment required", "justification": "Critical system outage"}'
```

**Block Request:**
```bash
# Block problematic request
curl -X POST https://onboarding.yourdomain.com/api/requests/{id}/block \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{"reason": "Security concern identified"}'
```

## Policy Management

### OPA Policy Updates

1. **Test Policies Locally:**
   ```bash
   # Validate policy syntax
   opa fmt opa/policies/onboarding.rego
   
   # Test policy decisions
   echo '{"input": {...}}' | opa eval -d opa/policies/ "data.onboarding.approval"
   ```

2. **Deploy Policy Updates:**
   ```bash
   # Update policies in production
   kubectl create configmap opa-policies \
     --from-file=opa/policies/ \
     -o yaml --dry-run=client | kubectl apply -f -
   
   # Restart OPA
   kubectl rollout restart deployment/opa -n aiops-platform
   ```

3. **Validate Deployment:**
   ```bash
   # Test policy endpoints
   curl -X POST http://opa.aiops-platform:8181/v1/data/onboarding/approval \
     -d '{"input": {...}}'
   ```

### Emergency Policy Override

For critical situations, temporary policy relaxation:

```bash
# Set permissive mode
kubectl patch configmap onboarding-config -n aiops-onboarding \
  -p '{"data":{"POLICY_MODE":"permissive"}}'

# Restart service to apply
kubectl rollout restart deployment/onboarding-service -n aiops-onboarding

# IMPORTANT: Remember to restore enforcing mode after emergency
```

## Audit & Compliance

### Audit Log Management

**Export Audit Logs:**
```bash
# Export all audit logs (JSON)
curl -H "Authorization: Bearer ADMIN_TOKEN" \
     "https://onboarding.yourdomain.com/api/audit/all?format=json" > audit_export.json

# Export specific request audit (CSV)
curl -H "Authorization: Bearer ADMIN_TOKEN" \
     "https://onboarding.yourdomain.com/api/audit/{request_id}?format=csv" > request_audit.csv
```

**Audit Analysis:**
```bash
# Count actions by user
jq '.[] | .user_id' audit_export.json | sort | uniq -c

# Find failed approvals
jq '.[] | select(.action == "approve" and .details.decision == "rejected")' audit_export.json

# Timeline analysis
jq '.[] | .timestamp' audit_export.json | sort
```

### Compliance Reporting

**Monthly Reports:**
- Total requests processed
- Approval workflow compliance rate
- Average processing time
- Security incidents (if any)
- Policy violations

**Annual Reports:**
- User access patterns
- System availability metrics
- Security audit results
- Process improvement recommendations

## System Health

### Health Monitoring

```bash
# Service health
curl https://onboarding.yourdomain.com/health

# Database connectivity
kubectl exec -it deployment/onboarding-service -n aiops-onboarding -- \
  python -c "from db import database; print('DB OK' if database.engine else 'DB Error')"

# OPA connectivity  
kubectl exec -it deployment/onboarding-service -n aiops-onboarding -- \
  python -c "import asyncio; from opa_client import opa_client; print(asyncio.run(opa_client.evaluate_policy('test', {})))"
```

### Performance Monitoring

Key metrics to monitor:
- Request processing latency
- Database query performance
- Authentication response time
- OPA policy evaluation time
- GitHub Actions dispatch success rate

### Capacity Planning

Monitor for scaling indicators:
- CPU/memory usage trends
- Database connection pool utilization
- Request queue lengths
- Response time percentiles

## Backup & Recovery

### Database Backups

```bash
# Daily backup
kubectl create cronjob onboarding-backup \
  --image=postgres:15 \
  --schedule="0 2 * * *" \
  -- pg_dump DATABASE_URL | gzip > /backup/onboarding-$(date +%Y%m%d).sql.gz

# Verify backup
gunzip -c /backup/onboarding-latest.sql.gz | head -50
```

### Configuration Backups

```bash
# Export Kubernetes manifests
kubectl get all,configmap,secret,ingress -n aiops-onboarding -o yaml > k8s-backup.yaml

# Export OPA policies
kubectl get configmap opa-policies -n aiops-platform -o yaml > opa-backup.yaml
```

### Recovery Procedures

**Service Recovery:**
1. Check pod status and logs
2. Verify database connectivity
3. Test authentication flow
4. Validate policy enforcement
5. Check GitHub integration

**Data Recovery:**
1. Stop service
2. Restore database from backup
3. Run migrations if needed
4. Restart service
5. Validate data integrity

## Security Operations

### Security Monitoring

Monitor for:
- Failed authentication attempts
- Unusual approval patterns
- Policy violations
- Privilege escalation attempts
- API abuse patterns

### Incident Response

**Security Incident Checklist:**
1. [ ] Identify scope of incident
2. [ ] Preserve audit logs
3. [ ] Block affected users if needed
4. [ ] Review access patterns
5. [ ] Update policies if required
6. [ ] Document incident and response

### Access Reviews

**Quarterly Access Review:**
1. Export user list with roles
2. Validate current role assignments
3. Remove inactive users
4. Update role mappings as needed
5. Document changes

## Troubleshooting

### Common Issues

**"Authentication Failed"**
- Check Keycloak service status
- Verify client configuration
- Test OIDC endpoints
- Review SSL certificates

**"Approval Denied by Policy"**
- Check user role assignments
- Verify OPA policy configuration
- Test policy logic independently
- Review approval history

**"Execution Failed"**
- Check GitHub token permissions
- Verify workflow configuration
- Test GitHub API connectivity
- Review error logs

**"Database Connection Error"**
- Check PostgreSQL service
- Verify connection credentials
- Test network connectivity
- Review database logs

### Debug Commands

```bash
# Check service logs
kubectl logs -f deployment/onboarding-service -n aiops-onboarding

# Test OPA policies
kubectl exec -it deployment/opa -n aiops-platform -- \
  opa eval -d /policies "data.onboarding.approval" --input input.json

# Validate database schema
kubectl exec -it deployment/postgres -n aiops-platform -- \
  psql -U onboarding_user -d aiops_onboarding -c "\d+"

# Test GitHub integration
kubectl exec -it deployment/onboarding-service -n aiops-onboarding -- \
  python -c "from github_dispatch import github_dispatcher; import asyncio; print(asyncio.run(github_dispatcher._mock_dispatch('test.yml', None)))"
```

## Maintenance Procedures

### Regular Maintenance

**Weekly:**
- Review security logs
- Check system performance
- Validate backup integrity
- Update monitoring dashboards

**Monthly:**
- Database maintenance (VACUUM, ANALYZE)
- Security updates
- Policy review
- User access audit

**Quarterly:**
- Full security assessment
- Disaster recovery testing
- Performance optimization
- Documentation updates

### Update Procedures

1. **Test in staging first**
2. **Schedule maintenance window**
3. **Backup current state**
4. **Deploy updates**
5. **Validate functionality**
6. **Monitor for issues**

For emergency support, contact the AIOps platform team with:
- Service logs
- Error messages
- Steps to reproduce
- Impact assessment