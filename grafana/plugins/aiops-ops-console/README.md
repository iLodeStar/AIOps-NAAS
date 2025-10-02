# AIOps Operations Console - Grafana App Plugin

A comprehensive operations console for AIOps-NAAS, implemented as a Grafana App Plugin for seamless integration with existing dashboards and monitoring infrastructure.

## Features

### Incident Management
- **List View**: Browse all incidents with filtering by severity, type, status, and ship
- **Detail View**: Comprehensive incident details with timeline, evidence, AI narratives, and runbooks
- **Status Management**: Acknowledge, resolve, or suppress incidents with audit trail
- **Search**: Quick search across incident types and descriptions

### Approvals
- **Two-Person Approval**: Enforce two-person authorization for high-risk actions
- **Pending Approvals**: View all actions awaiting approval
- **My Approvals**: Track your submitted approvals
- **Audit Trail**: All approvals logged to ops.audit NATS subject

### Action Center
- **Safe Actions**: Execute pre-approved, low-risk runbooks
- **Risk Assessment**: Clear risk indicators (low/medium/high)
- **Cooldown Enforcement**: Prevent accidental repeated execution
- **Pre/Post Checks**: Automated validation before and after execution
- **Parameter Validation**: Type-safe parameter input with defaults

### Policy Viewer
- **Read-Only Access**: View effective policy configuration on-ship
- **Segmented Display**: Browse policy by section (ingest, detect, correlate, etc.)
- **Source Tracking**: See if values are default, override, or fleet-wide
- **Diff View**: Compare ship policy against fleet default
- **GitOps Integration**: Propose changes through shore-side workflow

## Architecture

### Offline-First Design
- All API calls routed through Grafana's data source proxy
- No direct internet connectivity required
- Works seamlessly when ship is offline
- Local ClickHouse and NATS backend

### RBAC Integration
- **Viewer** → **Operator**: Read-only access to incidents and policy
- **Editor** → **Engineer**: Can approve actions and execute safe runbooks
- **Admin** → **Admin**: Full access to all features

### Technology Stack
- **Frontend**: React + TypeScript
- **UI Framework**: Grafana UI components
- **Routing**: React Router DOM
- **API Client**: Grafana Backend Service with data source proxy
- **Build Tool**: Grafana Toolkit

## Installation

### Development Mode

1. **Build the plugin:**
   ```bash
   cd grafana/plugins/aiops-ops-console
   npm install
   npm run build
   ```

2. **Link to Grafana:**
   ```bash
   # If using Docker Compose
   # The plugin directory is already mounted in docker-compose.yml
   
   # If using local Grafana
   ln -s $(pwd)/dist /var/lib/grafana/plugins/aiops-ops-console
   ```

3. **Enable the plugin in Grafana:**
   ```bash
   # Add to grafana.ini or set environment variable
   GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=aiops-ops-console
   ```

4. **Restart Grafana:**
   ```bash
   docker-compose restart grafana
   ```

5. **Activate the plugin:**
   - Navigate to Configuration → Plugins
   - Find "AIOps Operations Console"
   - Click "Enable"

### Production Deployment

1. **Sign the plugin** (requires Grafana Enterprise or Cloud account)
2. **Build for production:**
   ```bash
   npm run build
   ```
3. **Deploy** to Grafana plugins directory
4. **Configure data source proxy** for Incident API

## Configuration

### Data Source Proxy

Add to Grafana provisioning (`grafana/provisioning/datasources/datasources.yml`):

```yaml
apiVersion: 1

datasources:
  - name: AIOps Incident API
    type: prometheus  # Any type works for proxy
    uid: aiops-incident-api
    url: http://incident-api:9081
    access: proxy
    isDefault: false
    jsonData:
      httpMethod: GET
    secureJsonData: {}
```

### Feature Flags

Set environment variables for the Incident API service:

```bash
# Enable UI features
ENABLE_UI_APPROVALS=true
ENABLE_UI_ACTIONS=true
POLICY_READONLY=true

# RBAC
ENABLE_RBAC=true
RBAC_MODE=grafana  # Use Grafana roles
```

## Development

### Project Structure

```
grafana/plugins/aiops-ops-console/
├── src/
│   ├── api/
│   │   └── client.ts           # API client with all endpoints
│   ├── components/              # Reusable UI components
│   ├── pages/
│   │   ├── IncidentsPage.tsx   # Incident list view
│   │   ├── IncidentDetailPage.tsx  # Incident detail view
│   │   ├── ApprovalsPage.tsx   # Two-person approvals
│   │   ├── ActionsPage.tsx     # Safe action execution
│   │   └── PolicyPage.tsx      # Policy viewer
│   ├── types/
│   │   └── index.ts            # TypeScript type definitions
│   ├── utils/
│   │   └── helpers.ts          # Utility functions
│   ├── module.tsx              # Plugin entry point
│   └── plugin.json             # Plugin metadata
├── package.json
├── tsconfig.json
└── README.md
```

### Running in Development Mode

```bash
# Watch mode with hot reload
npm run watch

# Run tests
npm run test

# Type checking
npm run typecheck
```

### Adding New Features

1. Define types in `src/types/index.ts`
2. Add API methods in `src/api/client.ts`
3. Create page component in `src/pages/`
4. Add route in `src/module.tsx`
5. Update `src/plugin.json` includes section

## API Endpoints

The plugin expects the following endpoints from the Incident API:

### Incidents
- `GET /api/incidents` - List incidents with filters
- `GET /api/incidents/{id}` - Get incident details
- `PATCH /api/incidents/{id}` - Update incident status

### Approvals
- `GET /api/approvals/pending` - List pending approvals
- `GET /api/approvals/mine` - List my approvals
- `POST /api/incidents/{id}/approve` - Approve/reject action

### Actions
- `GET /api/actions` - List available actions
- `POST /api/actions/execute` - Execute action
- `GET /api/actions/executions/{id}` - Get execution result

### Policy
- `GET /api/policy` - Get effective policy
- `GET /api/policy/diff` - Get policy diff vs fleet default

### Audit
- `POST /api/audit` - Log audit event

## Testing

### Unit Tests
```bash
npm run test
```

### E2E Tests
```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run E2E tests
npm run test:e2e
```

### Manual Testing
1. Create test incidents via anomaly pipeline
2. Verify incident list and detail views
3. Test approval workflow with two users
4. Execute safe actions and verify results
5. Check audit trail in ops.audit NATS subject

## Troubleshooting

### Plugin Not Loading
- Check Grafana logs: `docker-compose logs grafana`
- Verify unsigned plugin is allowed
- Ensure plugin is built: `npm run build`

### API Calls Failing
- Check data source proxy configuration
- Verify Incident API is running
- Check network connectivity between Grafana and Incident API

### RBAC Not Working
- Verify Grafana user roles
- Check RBAC_MODE environment variable
- Review role mapping in `src/utils/helpers.ts`

## Acceptance Criteria

✅ Plugin pages render in Grafana with ship context selector  
✅ Incident list/detail supports status changes  
✅ Approvals enforce two-person rule with audit entries  
✅ Action Center executes only allowlisted, low-risk actions  
✅ Policy Viewer displays effective policy read-only  
✅ All network calls are local (offline-first)  
✅ RBAC enforced through Grafana roles  

## License

Apache 2.0 - See LICENSE file for details

## Support

For issues and feature requests, contact the AIOps NAAS team or create an issue in the repository.
