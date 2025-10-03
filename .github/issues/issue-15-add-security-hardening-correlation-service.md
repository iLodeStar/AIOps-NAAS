## Task
Add security hardening features to `services/correlation-service/` including authentication, TLS/SSL, and API security controls.

## Implementation

### 1. Authentication Layer
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

# Add API key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    expected_key = os.getenv("CORRELATION_API_KEY")
    if not expected_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    return api_key

# Protect endpoints
@app.get("/metrics", dependencies=[Depends(verify_api_key)])
async def metrics():
    ...
```

### 2. TLS/SSL Configuration
```python
# Update main() in correlation_service.py
if __name__ == "__main__":
    ssl_enabled = os.getenv("SSL_ENABLED", "false").lower() == "true"
    
    if ssl_enabled:
        ssl_keyfile = os.getenv("SSL_KEYFILE", "./certs/key.pem")
        ssl_certfile = os.getenv("SSL_CERTFILE", "./certs/cert.pem")
        
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=PORT,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile
        )
    else:
        uvicorn.run(app, host="0.0.0.0", port=PORT)
```

### 3. Enhanced Rate Limiting
```python
class EnhancedRateLimiter:
    """Rate limiter with request signing validation"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.suspicious_ips: Set[str] = set()
    
    def is_allowed(self, client_id: str, request_signature: Optional[str] = None) -> bool:
        # Check if IP is blocked
        if client_id in self.suspicious_ips:
            return False
        
        # Existing rate limit logic
        # Add signature validation for critical endpoints
        ...
```

### 4. Security Headers
```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response
```

### 5. Input Sanitization
```python
from aiops_core.utils import sanitize_ship_id

# Add input validation for all public endpoints
@app.get("/metrics")
async def metrics(ship_id: Optional[str] = None):
    if ship_id:
        ship_id = sanitize_ship_id(ship_id)  # Prevent injection attacks
    ...
```

### 6. Audit Logging
```python
async def log_security_event(event_type: str, client_id: str, details: Dict):
    """Log security-related events for audit trail"""
    security_event = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,  # auth_failure, rate_limit_exceeded, etc.
        "client_id": client_id,
        "details": details
    }
    
    # Publish to security.audit topic
    if service.nats:
        await service.nats.publish("security.audit", json.dumps(security_event).encode())
```

## Configuration

Add new environment variables:

```bash
# Authentication
CORRELATION_API_KEY=your-secret-api-key-here
API_KEY_ENABLED=true

# TLS/SSL
SSL_ENABLED=true
SSL_KEYFILE=/path/to/key.pem
SSL_CERTFILE=/path/to/cert.pem

# Security features
REQUEST_SIGNING_ENABLED=false
SECURITY_HEADERS_ENABLED=true
AUDIT_LOGGING_ENABLED=true
```

## Acceptance Criteria
- [ ] API key authentication implemented and configurable
- [ ] TLS/SSL support added for encrypted communication
- [ ] Enhanced rate limiting with IP blocking for suspicious activity
- [ ] Security headers added to all HTTP responses
- [ ] Input sanitization prevents injection attacks
- [ ] Audit logging captures security events
- [ ] Health endpoint remains accessible without auth (for monitoring)
- [ ] Documentation updated with security configuration guide
- [ ] Tests cover authentication and authorization flows

## Security Best Practices
1. **API Keys**: Store in environment variables, never in code
2. **TLS Certificates**: Use cert-manager or vault for certificate management
3. **Rate Limiting**: Monitor and adjust based on legitimate traffic patterns
4. **Audit Logs**: Ship to centralized SIEM for security monitoring
5. **Principle of Least Privilege**: Only authenticate what needs protection

## Testing
```python
# Add security tests
def test_api_key_required():
    response = client.get("/metrics")
    assert response.status_code == 401

def test_valid_api_key():
    headers = {"X-API-Key": "valid-key"}
    response = client.get("/metrics", headers=headers)
    assert response.status_code == 200

def test_rate_limit_blocks_excessive_requests():
    # Simulate attack scenario
    ...
```

**Effort**: 6-8h | **Priority**: High | **Dependencies**: #162 (Correlation Service)

## Notes
- Start with API key authentication as it's simplest to implement
- TLS/SSL can be handled at load balancer/ingress level initially
- Consider OAuth2/JWT for future multi-tenant deployments
- Rate limiting enhancements should be backward compatible
- Coordinate with security team for key management strategy
