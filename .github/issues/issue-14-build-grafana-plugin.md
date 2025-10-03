## Task
Build Grafana Operations Console plugin.

## Build Steps

```bash
cd grafana/plugins/aiops-ops-console
npm install
npm run build       # Development
npm run build:prod  # Production
```

## Testing
1. Copy plugin to Grafana plugins directory
2. Restart Grafana
3. Enable plugin in UI
4. Test pages: Incidents, Approvals, Actions, Policy
5. Verify API integration

## Acceptance Criteria
- [ ] `npm install` succeeds
- [ ] `npm run build` produces dist/
- [ ] Plugin loads in Grafana
- [ ] All 4 pages render
- [ ] API calls work
- [ ] No console errors

**Effort**: 2h | **Priority**: Low | **Dependencies**: #4
