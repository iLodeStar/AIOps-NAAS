# AIOps Operations Console - Implementation Guide

## Overview

The AIOps Operations Console is implemented as a **Grafana App Plugin** that provides a unified interface for incident management, action approvals, safe runbook execution, and policy viewing. This approach minimizes operational complexity while providing rich functionality.

## Architecture Decision

### Why Grafana Plugin vs Standalone SPA?

**Decision**: Use Grafana App Plugin instead of standalone React application

**Rationale**:
1. **Team Size**: 3-4 engineers benefit from reduced surface area
2. **Operational Simplicity**: No new service to deploy, scale, or secure
3. **Familiar UX**: Operators stay in Grafana for all operational tasks
4. **Cost/Time**: Faster delivery with smaller code surface
5. **Offline-First**: Plugin runs inside on-ship Grafana instance
6. **Future-Proof**: Can extract to standalone SPA if needed

### Integration with Version 3 Architecture

The Ops Console integrates seamlessly with the Version 3 architecture:

- **Fast Path**: Incident viewing is real-time from ClickHouse
- **Insight Path**: AI narratives displayed asynchronously when available
- **Offline-First**: All API calls are local (NATS + ClickHouse)
- **Low Latency**: Sub-second incident queries via ClickHouse
- **Policy-Driven**: All actions enforced through OPA policies

## Components

### 1. Grafana App Plugin

**Location**: `grafana/plugins/aiops-ops-console/`

**Pages**:
- **Incidents** (`/incidents`) - List and search incidents
- **Incident Detail** (`/incidents/:id`) - Full incident view with tabs
- **Approvals** (`/approvals`) - Two-person approval workflow
- **Actions** (`/actions`) - Safe runbook execution
- **Policy** (`/policy`) - Read-only policy viewer

**Technology**:
- TypeScript + React
- Grafana UI components
- React Router for navigation
- Grafana Runtime for API proxy

### 2. Backend API Extensions

**Location**: `services/incident-api/api_extensions.py`

**New Endpoints**:

#### Approvals
- `GET /api/approvals/pending` - List pending approvals
- `GET /api/approvals/mine` - List my approvals
- `POST /api/incidents/{id}/approve` - Approve/reject with two-person enforcement

#### Actions
- `GET /api/actions` - List available actions with cooldown status
- `POST /api/actions/execute` - Execute action with pre/post checks
- `GET /api/actions/executions/{id}` - Get execution result

#### Policy
- `GET /api/policy` - Get effective policy (read-only)
- `GET /api/policy/diff` - Compare with fleet default

#### Audit
- `POST /api/audit` - Log audit event to ops.audit NATS subject
- `GET /api/audit` - Query audit log

### 3. Data Source Proxy

**Location**: `grafana/provisioning/datasources/incident-api.yml`

Configures Grafana to proxy API requests to the Incident API service, avoiding CORS issues and maintaining offline-first architecture.

## Features

### Incident Management

**List View**:
- Filter by severity, type, status, ship_id
- Search across incident descriptions
- Pagination support
- Real-time updates

**Detail View**:
- Summary with AI narrative (async)
- Timeline of events
- Evidence links to ClickHouse
- Recommended runbooks
- Status actions: Acknowledge, Resolve, Suppress

### Approval Workflow

**Two-Person Rule**:
- High-risk actions require two approvals
- First approver moves status to "partial"
- Second approver completes approval
- All approvals logged to ops.audit

**Features**:
- Pending approvals queue
- My approvals history
- Action preview before approval
- Comment/rejection with reason
- Policy excerpt display

### Action Center

**Safe Execution**:
- Only pre-approved actions from policy
- Risk level indicators (low/medium/high)
- Cooldown enforcement prevents accidents
- Parameter validation with types
- Pre-checks before execution
- Post-checks after completion

**Available Actions** (from policy):
- restart_service (low risk, 5min cooldown)
- rotate_logs (low risk, 10min cooldown)
- failover_path (medium risk, 30min cooldown, two-person)

### Policy Viewer

**Read-Only Display**:
- Segmented by section (ingest, detect, correlate, etc.)
- Source indicators (default/override/fleet)
- Effective value highlighting
- Diff vs fleet default (when available)
- GitOps proposal stub for future

## RBAC Integration

### Role Mapping

Grafana roles are mapped to Operator roles:

| Grafana Role | Operator Role | Permissions |
|--------------|---------------|-------------|
| Viewer | Operator | Read-only: incidents, policy |
| Editor | Engineer | + Approve actions, execute safe runbooks |
| Admin | Admin | + All administrative functions |

### Enforcement

RBAC is enforced at multiple levels:
1. **Plugin Level**: Route guards in React
2. **API Level**: Endpoint authorization checks
3. **Policy Level**: OPA policy enforcement

## Installation

### Prerequisites

- Grafana v10.0+
- Node.js 18+
- Docker Compose environment

### Quick Setup

1. **Build the plugin:**
   ```bash
   cd grafana/plugins/aiops-ops-console
   npm install
   npm run build
   ```

2. **Mount plugin in Grafana** (already configured in docker-compose.yml):
   ```yaml
   grafana:
     volumes:
       - ./grafana/plugins/aiops-ops-console/dist:/var/lib/grafana/plugins/aiops-ops-console
   ```

3. **Allow unsigned plugin**:
   ```yaml
   grafana:
     environment:
       - GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=aiops-ops-console
   ```

4. **Restart Grafana**:
   ```bash
   docker-compose restart grafana
   ```

5. **Enable plugin in UI**:
   - Navigate to Configuration → Plugins
   - Search for "AIOps Operations Console"
   - Click "Enable"

### Data Source Configuration

The datasource is automatically provisioned from `grafana/provisioning/datasources/incident-api.yml`. No manual configuration needed.

## Testing

### Manual Testing

1. **Incidents**:
   ```bash
   # Create test incident
   echo '{"incident_id":"test-001", "severity":"high", "type":"link_degradation", "ship_id":"test-ship"}' | \
     curl -X POST http://localhost:9081/api/incidents -d @-
   
   # View in UI
   open http://localhost:3000/a/aiops-ops-console/incidents
   ```

2. **Approvals**:
   - Navigate to Actions
   - Execute "Failover to Backup Path" (requires two-person)
   - Navigate to Approvals
   - Approve as first user
   - Log in as second user and approve again

3. **Actions**:
   - Navigate to Action Center
   - Execute "Restart Service"
   - Verify cooldown prevents re-execution
   - Check execution result

4. **Policy**:
   - Navigate to Policy
   - Browse different sections
   - Verify read-only mode

### Automated Testing

```bash
# Unit tests
cd grafana/plugins/aiops-ops-console
npm run test

# E2E tests (TODO)
npm run test:e2e
```

## Configuration

### Feature Flags

Set in incident-api service environment:

```yaml
incident-api:
  environment:
    - ENABLE_UI_APPROVALS=true
    - ENABLE_UI_ACTIONS=true
    - POLICY_READONLY=true
    - RBAC_MODE=grafana
```

### Policy Configuration

Edit `policies/policy.example.yaml`:

```yaml
remediate:
  allowed_actions:
    - restart_service
    - rotate_logs
    - failover_path
  human_in_the_loop_default: true
  two_person_approval_for:
    - network_changes
    - firewall_policies
```

### Action Definitions

Actions are defined in `services/incident-api/api_extensions.py`:

```python
_action_definitions = [
    {
        "action_id": "restart_service",
        "name": "Restart Service",
        "risk": "low",
        "cooldown_sec": 300,
        "parameters": [...]
    }
]
```

## Deployment

### Development

```bash
# Start entire stack
docker-compose up -d

# Watch plugin for changes
cd grafana/plugins/aiops-ops-console
npm run watch
```

### Production

1. Build plugin for production
2. Sign plugin (if using Grafana Enterprise)
3. Deploy to production Grafana
4. Configure HTTPS/TLS
5. Enable authentication
6. Set production feature flags

## Monitoring

### Plugin Health

- Check Grafana logs: `docker-compose logs grafana`
- Monitor plugin load time
- Track API response times

### API Health

- Monitor incident-api metrics
- Check NATS consumer lag
- Verify ClickHouse query performance

### User Activity

- Track action executions in ops.audit
- Monitor approval workflow latency
- Review incident status transitions

## Troubleshooting

### Plugin Not Loading

**Symptoms**: Plugin doesn't appear in Grafana
**Solutions**:
- Check `GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS` is set
- Verify plugin is built: `ls -la dist/`
- Check Grafana logs for errors
- Restart Grafana

### API Calls Failing

**Symptoms**: "Failed to load" errors in UI
**Solutions**:
- Verify datasource proxy is configured
- Check incident-api is running
- Test API directly: `curl http://localhost:9081/api/incidents`
- Check network between Grafana and incident-api

### RBAC Not Working

**Symptoms**: Users see unauthorized errors
**Solutions**:
- Verify Grafana user roles
- Check RBAC_MODE=grafana is set
- Review role mapping logic
- Test with different user roles

### Actions Not Executing

**Symptoms**: Execute button disabled
**Solutions**:
- Check action allowlist in policy
- Verify cooldown has expired
- Check action requires_approval status
- Review OPA policy enforcement

## Acceptance Criteria

✅ Plugin pages render in Grafana with proper navigation  
✅ Incident list/detail supports filtering and status changes  
✅ Approvals enforce two-person rule with audit trail  
✅ Action Center executes only allowlisted actions  
✅ Cooldowns prevent accidental repeated execution  
✅ Policy Viewer displays read-only configuration  
✅ All network calls are local (offline-first verified)  
✅ RBAC enforced through Grafana roles  
✅ No separate build/deploy surface required  

## Future Enhancements

### Short Term
- Add incident assignment workflow
- Implement notification preferences
- Add action scheduling
- Enhance policy diff visualization

### Medium Term
- Extract to standalone SPA if needed
- Add mobile-responsive views
- Implement real-time updates via WebSocket
- Add advanced filtering and saved views

### Long Term
- Full policy editing (shore-side)
- Cross-ship incident correlation UI
- Predictive incident forecasting dashboard
- ML model management console

## References

- [Version 3 Architecture](../SYSTEM_ARCHITECTURE_Version3.md)
- [NATS Subjects](../NATS_SUBJECTS_Version2.md)
- [Data Contracts](../DATA_CONTRACTS_Version2.md)
- [Profiles and Flags](../PROFILES_AND_FLAGS_Version2.md)
- [Plugin README](../grafana/plugins/aiops-ops-console/README.md)

## Support

For issues and questions:
1. Check Grafana plugin logs
2. Review incident-api logs
3. Check NATS message flow
4. Review audit trail in ops.audit
5. Contact AIOps NAAS team

---

**Status**: ✅ Implementation Complete  
**Last Updated**: 2025-10-02  
**Version**: 1.0.0
