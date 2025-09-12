# System Syslog Support in One-Click Incident Debugging

The one-click incident debugging tool now includes comprehensive support for **system-generated syslog data**, enabling end-to-end testing with authentic system service logs.

## 🖥️ System Services Supported

### Core System Services
- **systemd** (facility 1) - Service management, startup, failures
- **sshd** (facility 4) - Authentication events, login attempts
- **kernel** (facility 0) - Hardware events, temperature, disk errors
- **cron** (facility 9) - Scheduled job execution, backup tasks
- **networkd** (facility 3) - Network interface changes, connectivity

### Maritime-Specific Services  
- **GPS daemon** (facility 16) - Navigation accuracy, fix loss
- **Engine monitoring** (facility 16) - Performance metrics, alerts
- **Communication systems** (facility 16) - Radio, satellite connectivity

## 🔌 Transport Methods

### Vector Syslog Sources
- **UDP Port 1514** - Primary Vector syslog UDP source
- **TCP Port 1516** - Primary Vector syslog TCP source  
- **UDP Port 514** - Standard syslog (requires root privileges)
- **HTTP API** - Fallback method via Vector REST API

### Message Format Support
- **RFC 5424** - Modern syslog format with structured data
- **RFC 3164** - Legacy syslog format (BSD syslog)
- **Custom facilities** - Proper facility codes for different service types

## 🧪 Testing Capabilities

### One-Click Debugger Enhancements
```bash
# Run complete system syslog diagnostic
python3 scripts/one_click_incident_debugging.py --deep-analysis --generate-issue-report
```

**New Features:**
- 🖥️ **System service test scenarios** - Real systemd, sshd, kernel message patterns
- 📡 **Multi-transport testing** - UDP/TCP/HTTP delivery methods
- 🏷️ **Proper facility codes** - Kernel (0), user (1), security (4), cron (9), local (16+)
- 📊 **Syslog port health checks** - Connectivity testing for all Vector syslog sources
- 📈 **Vector syslog metrics** - Component activity monitoring

### Dedicated System Syslog Tester
```bash
# Run focused system syslog tests
./scripts/test_system_syslog.sh
```

**Capabilities:**
- Tests 6 different system service types
- Uses proper syslog facilities and priorities
- Validates message delivery through entire pipeline
- Generates comprehensive test reports

## 🔍 Diagnostic Features

### Enhanced Data Analysis
- **Service type detection** - Distinguishes system vs application logs
- **Facility code validation** - Ensures proper syslog categorization  
- **Transport method verification** - Tests all available delivery paths
- **Hostname extraction** - System service hostname → ship_id mapping

### Improved Reproduction Steps
Generated issue reports now include:
- **System-specific syslog commands** with proper facility codes
- **Multiple transport examples** (UDP 1514, TCP 1516, standard 514)
- **Service-specific message patterns** for systemd, sshd, kernel, etc.
- **Expected behavior documentation** for each system service type

## 📋 Configuration Requirements

### Vector Configuration
```toml
# Vector syslog sources are already configured
[sources.syslog_udp]
type = "syslog"
address = "0.0.0.0:1514" 
mode = "udp"

[sources.syslog_tcp]
type = "syslog"
address = "0.0.0.0:1516"
mode = "tcp"
```

### Device Registry Mappings
System hostnames must be registered for ship_id resolution:
```bash
curl -X POST http://localhost:8091/devices \
  -H 'Content-Type: application/json' \
  -d '{
    "hostname": "ship-bridge-01",
    "ship_id": "vessel-alpha", 
    "device_type": "system",
    "location": "bridge"
  }'
```

## 🏗️ Integration Architecture

```
System Services → Syslog → Vector → NATS → Benthos → ClickHouse → Incident API
     ↓              ↓        ↓       ↓       ↓         ↓            ↓
[systemd/sshd] [UDP/TCP] [Parse] [Stream] [Transform] [Store] [Alert/API]
[kernel/cron]  [1514/16] [Enrich] [Route] [Enhance] [Query] [Dashboard]
```

### Data Flow
1. **System services** generate syslog messages with proper facilities
2. **Vector syslog sources** receive via UDP/TCP on ports 1514/1516  
3. **Vector transforms** extract hostname, service, message, timestamp
4. **Device registry lookup** resolves hostname → ship_id mapping
5. **NATS streaming** routes enriched messages to processing pipeline
6. **Benthos processing** applies business logic and data enhancement
7. **ClickHouse storage** persists structured incident records
8. **Incident API** provides query interface and alerting

## 📊 Monitoring & Metrics

### Vector Syslog Metrics
```bash
# Monitor syslog component activity
curl http://localhost:8686/metrics | grep syslog

# Check message throughput
curl http://localhost:8686/metrics | grep vector_component_sent_events_total
```

### ClickHouse Queries  
```sql
-- System syslog incidents by service type
SELECT service, COUNT(*) as incident_count 
FROM logs.incidents 
WHERE source = 'syslog' 
GROUP BY service 
ORDER BY incident_count DESC;

-- Recent system service alerts
SELECT ship_id, service, message, processing_timestamp
FROM logs.incidents 
WHERE source = 'syslog' 
  AND service IN ('systemd', 'sshd', 'kernel', 'cron')
ORDER BY processing_timestamp DESC 
LIMIT 20;
```

## 🚀 Usage Examples

### Test System Authentication Events
```bash
# Simulate SSH authentication failure
echo '<38>1 2024-01-01T00:00:00Z ship-bridge-01 sshd - - Failed password for maintenance from 192.168.1.100 port 22 ssh2' | nc -u localhost 1514

# Simulate systemd service restart
echo '<14>1 2024-01-01T00:00:00Z ship-engine-02 systemd - - Started engine monitoring service after failure' | nc localhost 1516
```

### Test Kernel Hardware Events  
```bash
# Simulate temperature alert
echo '<6>1 2024-01-01T00:00:00Z ship-sensor-03 kernel - - Hardware temperature sensor reading 85.2°C on CPU thermal zone' | nc -u localhost 1514

# Simulate disk error
echo '<3>1 2024-01-01T00:00:00Z ship-storage-01 kernel - - I/O error on device sda, sector 12345' | nc localhost 1516
```

### Verify Processing
```bash  
# Check incident creation
docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin \
  --query="SELECT * FROM logs.incidents WHERE service IN ('sshd', 'systemd', 'kernel') ORDER BY processing_timestamp DESC LIMIT 10"
```

## 🔧 Troubleshooting

### Common Issues

**Port 514 Access Denied**
- Standard syslog port requires root privileges
- Use Vector ports 1514/1516 instead
- Container runs as non-root by design

**Missing Ship ID Resolution**  
- Ensure hostname is registered in device registry
- Check device registry health: `curl http://localhost:8091/health`
- Verify hostname extraction in Vector logs

**Facility Code Confusion**
- Kernel: 0, User: 1, Security: 4, Cron: 9, Local: 16-23
- Priority = facility * 8 + severity (0-7)
- Use appropriate facility for service type

### Debug Commands
```bash
# Test port connectivity
nc -u -z localhost 1514  # Vector UDP
nc -z localhost 1516     # Vector TCP

# Monitor Vector logs
docker-compose logs vector | grep syslog

# Check NATS message flow
docker exec aiops-nats nats stream ls
docker exec aiops-nats nats stream view STREAM_NAME
```

## 📈 Production Recommendations

### Syslog Configuration
- Configure system services to send logs to Vector syslog ports
- Use structured logging where possible (JSON in message field)
- Include tracking IDs for correlation and debugging
- Set appropriate log levels to avoid noise

### Monitoring Setup
- Monitor Vector syslog component metrics
- Alert on syslog ingestion rate drops
- Track device registry resolution failures  
- Monitor ClickHouse syslog table growth

### Security Considerations
- Restrict syslog port access to authorized systems only
- Use TLS for TCP syslog in production environments  
- Implement rate limiting to prevent log flooding
- Sanitize sensitive data in log messages

---

This comprehensive system syslog support enables the AIOps platform to effectively process and analyze logs from all ship system services, providing complete observability for maritime operations.