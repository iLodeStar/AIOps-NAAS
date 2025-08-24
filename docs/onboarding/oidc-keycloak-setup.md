# OIDC Keycloak Setup for Onboarding Service

## Overview

This guide provides step-by-step instructions for configuring Keycloak as the OIDC identity provider for the AIOps Onboarding Service.

## Prerequisites

- Keycloak 22.0+ installed and running
- Administrative access to Keycloak
- Network connectivity between onboarding service and Keycloak

## Keycloak Configuration

### 1. Create AIOps Realm

```bash
# Login to Keycloak admin console
# http://localhost:8080 (development)
# https://keycloak.yourdomain.com (production)
```

1. Navigate to "Realm settings"
2. Click "Create Realm"
3. **Realm name**: `aiops`
4. **Display name**: `AIOps Platform`
5. **Enabled**: ON
6. Click "Create"

### 2. Configure Realm Settings

**General Tab:**
- **Display name**: AIOps Platform
- **Frontend URL**: (leave empty for auto-detection)
- **Require SSL**: External requests (production) / None (development)

**Login Tab:**
- **User registration**: OFF (controlled registration)
- **Forgot password**: ON
- **Remember me**: ON
- **Login with email**: ON

**Email Tab:**
- Configure SMTP settings for password reset and notifications

**Tokens Tab:**
- **Access token lifespan**: 24 hours
- **Access token lifespan for implicit flow**: 1 hour
- **Client login timeout**: 24 hours
- **Offline session idle timeout**: 30 days

### 3. Create Onboarding Service Client

1. Navigate to "Clients" → "Create client"
2. **Client type**: OpenID Connect
3. **Client ID**: `onboarding-service`
4. Click "Next"

**Capability config:**
- **Client authentication**: ON (confidential client)
- **Authorization**: OFF
- **Standard flow**: ON
- **Direct access grants**: ON (for API access)
- **Implicit flow**: OFF
- **Service accounts roles**: ON (for service-to-service calls)

**Login settings:**
- **Root URL**: `http://localhost:8090` (development)
- **Home URL**: `/`
- **Valid redirect URIs**: `/auth/callback`
- **Valid post logout redirect URIs**: `/`
- **Web origins**: `*` (development) / specific origins (production)

### 4. Client Authentication

Navigate to "Clients" → "onboarding-service" → "Credentials":

- **Client Authenticator**: Client Id and Secret
- **Secret**: (generated automatically - copy this value)

**Store the client secret securely:**

```bash
# Development
export OIDC_CLIENT_SECRET="your-generated-secret"

# Production
kubectl create secret generic onboarding-secrets \
  --from-literal=oidc-client-secret="your-generated-secret"
```

### 5. Create Realm Roles

Navigate to "Realm roles" → "Create role":

1. **aiops-requester**
   - Description: "Can create and submit onboarding requests"
   - Composite: OFF

2. **aiops-deployer**
   - Description: "Can provide deployer approvals and execute deployments"
   - Composite: OFF

3. **aiops-authoriser**
   - Description: "Can provide authoriser approvals for requests"
   - Composite: OFF

4. **aiops-admin**
   - Description: "Full administrative access to onboarding service"
   - Composite: ON
   - Associated roles: All aiops-* roles

5. **aiops-viewer**
   - Description: "Read-only access to requests and audit logs"
   - Composite: OFF

### 6. Configure Client Scopes

Navigate to "Client scopes" → "Create client scope":

1. **aiops-roles**
   - **Name**: aiops-roles
   - **Description**: AIOps platform roles
   - **Type**: Default
   - **Include in token scope**: ON

**Add Mappers:**

1. **Realm roles mapper**:
   - **Name**: realm-roles
   - **Mapper type**: User Realm Role
   - **Token claim name**: realm_access.roles
   - **Claim JSON Type**: String array
   - **Add to ID token**: ON
   - **Add to access token**: ON
   - **Add to userinfo**: ON

2. **Client roles mapper**:
   - **Name**: client-roles
   - **Mapper type**: User Client Role
   - **Client ID**: onboarding-service
   - **Token claim name**: resource_access.${client_id}.roles
   - **Add to ID token**: ON
   - **Add to access token**: ON

**Assign to Client:**
1. Navigate to "Clients" → "onboarding-service" → "Client scopes"
2. Click "Add client scope"
3. Select "aiops-roles"
4. Set to "Default"

### 7. Create Groups (Recommended)

Navigate to "Groups" → "Create group":

1. **AIOps Requesters**
   - Assign role: `aiops-requester`

2. **AIOps Deployers**
   - Assign role: `aiops-deployer`

3. **AIOps Authorisers**
   - Assign role: `aiops-authoriser`

4. **AIOps Administrators**
   - Assign role: `aiops-admin`

5. **AIOps Viewers**
   - Assign role: `aiops-viewer`

### 8. Create Test Users

Navigate to "Users" → "Create new user":

1. **Test Requester**
   - **Username**: test-requester
   - **Email**: requester@cruise.local
   - **First name**: Test
   - **Last name**: Requester
   - **Groups**: AIOps Requesters

2. **Test Deployer**
   - **Username**: test-deployer
   - **Email**: deployer@cruise.local
   - **Groups**: AIOps Deployers

3. **Test Authoriser**
   - **Username**: test-authoriser
   - **Email**: authoriser@cruise.local
   - **Groups**: AIOps Authorisers

4. **Test Admin**
   - **Username**: test-admin
   - **Email**: admin@cruise.local
   - **Groups**: AIOps Administrators

**Set Passwords:**
1. Select user → "Credentials"
2. Set password
3. **Temporary**: OFF
4. Click "Set password"

## Service Configuration

### Environment Variables

```bash
# OIDC Configuration
OIDC_ISSUER_URL=http://keycloak:8080/realms/aiops
OIDC_CLIENT_ID=onboarding-service
OIDC_CLIENT_SECRET=your-client-secret-from-keycloak
OIDC_REDIRECT_URI=http://localhost:8090/auth/callback

# Security
SECRET_KEY=your-secure-random-secret-key

# Application
DEBUG=false
```

### Docker Compose Integration

```yaml
version: '3.8'
services:
  keycloak:
    image: quay.io/keycloak/keycloak:22.0
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: password
    ports:
      - "8080:8080"
    command: start-dev
    depends_on:
      - postgres

  onboarding-service:
    build: ./services/onboarding-service
    environment:
      OIDC_ISSUER_URL: http://keycloak:8080/realms/aiops
      OIDC_CLIENT_ID: onboarding-service
      OIDC_CLIENT_SECRET: your-client-secret
      OIDC_REDIRECT_URI: http://localhost:8090/auth/callback
    ports:
      - "8090:8090"
    depends_on:
      - keycloak
```

## Testing OIDC Integration

### 1. Test Discovery Endpoint

```bash
curl -s http://keycloak:8080/realms/aiops/.well-known/openid_configuration | jq .
```

Verify the response includes:
- `authorization_endpoint`
- `token_endpoint`
- `userinfo_endpoint`
- `jwks_uri`

### 2. Test Authentication Flow

1. Navigate to onboarding service: `http://localhost:8090`
2. Click "Login"
3. Should redirect to Keycloak login page
4. Login with test credentials
5. Should redirect back to onboarding service dashboard
6. Verify user roles are displayed correctly

### 3. Test Token Claims

Enable debug mode and check logs for token contents:

```bash
DEBUG=true uvicorn app:app --reload
```

Look for log entries showing decoded token with:
- `sub` (user ID)
- `email`
- `name`
- `realm_access.roles` (array of roles)

### 4. Test Role Mapping

Verify role mapping by:
1. Login as each test user
2. Check displayed roles on dashboard
3. Test role-specific permissions:
   - Requester: Can create requests
   - Deployer: Can approve as deployer
   - Authoriser: Can approve as authoriser
   - Admin: Can perform all actions

## Troubleshooting

### Common Issues

**"Invalid client credentials"**
- Verify client secret matches Keycloak configuration
- Check client authentication is enabled
- Ensure client ID is correct

**"Invalid redirect URI"**
- Check redirect URI is registered in Keycloak client
- Verify protocol (http/https) matches
- Ensure no trailing slashes or extra parameters

**"No roles found"**
- Check realm role mapper configuration
- Verify user has assigned roles
- Check client scope includes roles

**"Token validation failed"**
- Verify issuer URL is accessible from service
- Check network connectivity to Keycloak
- Ensure issuer URL includes /realms/aiops

### Debug Commands

```bash
# Test Keycloak connectivity
curl -f http://keycloak:8080/realms/aiops/.well-known/openid_configuration

# Test client credentials
curl -X POST http://keycloak:8080/realms/aiops/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=onboarding-service&client_secret=SECRET"

# Validate token
curl http://keycloak:8080/realms/aiops/protocol/openid-connect/userinfo \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

### Log Analysis

Enable detailed logging:

```bash
# Keycloak debug
KC_LOG_LEVEL=DEBUG

# Service debug
DEBUG=true
LOG_LEVEL=DEBUG
```

Check logs for:
- OIDC discovery calls
- Token exchange requests
- Role mapping results
- Session creation/validation

## Production Deployment

### Security Checklist

- [ ] HTTPS enabled with valid certificates
- [ ] Client secrets stored securely
- [ ] Database encrypted at rest
- [ ] Network access restricted
- [ ] Audit logging enabled
- [ ] Regular backup configured
- [ ] Role assignments reviewed
- [ ] Token lifetimes configured appropriately
- [ ] Monitoring and alerting set up

### High Availability

For production HA setup:
1. **Keycloak Cluster**: Multiple Keycloak instances with shared database
2. **Load Balancer**: Distribute traffic across instances
3. **Database**: PostgreSQL cluster for Keycloak data
4. **Session Replication**: Configure Keycloak session sharing
5. **Health Checks**: Monitor Keycloak and service health

### Monitoring Integration

Monitor key metrics:
- Authentication success/failure rates
- Token validation latency
- Role assignment changes
- Session duration statistics
- Failed authorization attempts