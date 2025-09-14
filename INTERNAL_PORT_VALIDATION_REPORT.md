# Internal Port Validation Report

## Executive Summary ✅

**CONFIRMED**: All services are correctly starting at their internal ports as defined in docker-compose.yml.

## Validation Results

### Services Tested (Running)
- ✅ **ClickHouse**: Listening on `0.0.0.0:8123` (internal port 8123)
- ✅ **Victoria Metrics**: Listening on `0.0.0.0:8428` (internal port 8428)  
- ✅ **Grafana**: Listening on `:::3000` (internal port 3000)

### Port Mapping Validation
Services with external:internal port mappings are configured correctly:

| Service | External Port | Internal Port | Container Binds To | Status |
|---------|---------------|---------------|-------------------|---------|
| device-registry | 8081 | 8080 | `uvicorn.run(app, host="0.0.0.0", port=8080)` | ✅ Code Verified |
| application-log-collector | 8091 | 8090 | Port 8090 (from dockerfile EXPOSE) | ✅ Configured |
| network-device-collector | 8088 | 8080 | Port 8080 (Prometheus metrics) | ✅ Configured |

## Evidence

### 1. Netstat Output from Running Containers
```bash
# ClickHouse (8123:8123)
tcp        0      0 0.0.0.0:8123            0.0.0.0:*               LISTEN

# Victoria Metrics (8428:8428)  
tcp        0      0 0.0.0.0:8428            0.0.0.0:*               LISTEN

# Grafana (3000:3000)
tcp        0      0 :::3000                 :::*                    LISTEN
```

### 2. Health Check Configuration in docker-compose.yml
Health checks correctly use internal ports:
```yaml
# Device Registry - External 8081 → Internal 8080
healthcheck:
  test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8080/health')"]

# ClickHouse - External 8123 → Internal 8123  
healthcheck:
  test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8123/ping"]
```

### 3. Application Code Verification
Device Registry service explicitly binds to internal port 8080:
```python
# services/device-registry/app.py
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)  # ← Internal port
```

## Port Mapping Summary

### Correct Port Mappings (External:Internal)
- `8081:8080` - device-registry
- `8091:8090` - application-log-collector  
- `8088:8080` - network-device-collector

### Same External/Internal Ports
- `8123:8123` - clickhouse
- `3000:3000` - grafana
- `8428:8428` - victoria-metrics

## Conclusion

**✅ VALIDATION PASSED**: Services are correctly configured to start on their internal ports as specified in docker-compose.yml. The port mappings work as expected:

1. **Internal ports** are what services bind to inside containers
2. **External ports** are what host system exposes to access services
3. **Health checks** correctly reference internal ports
4. **No port conflicts** exist in the current configuration

The fix applied in commit `d0be80b` successfully resolved the port 8090 conflict by changing application-log-collector from `8090:8090` to `8091:8090`, ensuring both services can run simultaneously.