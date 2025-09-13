# Quick Reference Card - AIOps NAAS Diagnostics

## 🚀 Quick Commands

### Run Diagnostics
```bash
# Quick health check (5 minutes)
python3 scripts/user_friendly_diagnostics.py --mode sanity

# Full system test (15 minutes)  
python3 scripts/user_friendly_diagnostics.py --mode regression

# Watch system (15 minutes, no test data)
python3 scripts/user_friendly_diagnostics.py --mode surveillance

# Full autonomous test (1 hour)
python3 scripts/user_friendly_diagnostics.py --mode automation
```

### Check System Status
```bash
# Check all services
docker compose ps

# Check specific service logs
docker compose logs [service-name]

# Restart services
docker compose restart
```

## 📊 Understanding Results

| Symbol | Meaning | Action Needed |
|--------|---------|---------------|
| ✅ | Success | None - working perfectly |
| ⚠️  | Warning | Monitor, may need attention |
| ❌ | Error | Immediate action required |
| ℹ️  | Info | Just information, no action |

## 🎯 Quick Troubleshooting

### "Docker not running"
```bash
# Check Docker status
docker ps
# Start Docker (Linux)
sudo systemctl start docker
```

### "Services down"
```bash
# Check which services
docker compose ps
# Restart all
docker compose restart
```

### "No data in system"
```bash
# Check Vector logs
docker compose logs vector
# Check ClickHouse
curl http://localhost:8123/ping
```

## 🌐 Quick Access URLs

- **Grafana Dashboards**: http://localhost:3000 (admin/admin)
- **ClickHouse Query**: http://localhost:8123/play
- **System Health**: http://localhost:8686/health
- **NATS Monitoring**: http://localhost:8222

## 📞 Need Help?

1. Save diagnostic output: `--output results.json`
2. Note your Session ID (shown at start)
3. Screenshot any error messages
4. Check logs: `/tmp/aiops_diagnostics.log`

## 🔄 Testing Modes At A Glance

| Mode | Duration | Purpose | When to Use |
|------|----------|---------|-------------|
| **Sanity** | 5 min | Quick health check | Daily, after changes |
| **Regression** | 15 min | Full system test | Weekly, troubleshooting |
| **Surveillance** | 15 min | Watch real data | Baseline, investigation |
| **Automation** | 1 hour | Full autonomous | Monthly, certification |

## 🏥 Health Check Checklist

- [ ] All Docker services running
- [ ] Green checkmarks in diagnostic output  
- [ ] Normal messages stored in database
- [ ] Anomaly messages create incidents
- [ ] All system URLs accessible

---
*Keep this card handy for quick reference during system operations!*