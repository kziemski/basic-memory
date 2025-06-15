# Basic Memory Authentication

Basic Memory uses JWT-based authentication for secure, multi-tenant deployments. This document describes how authentication works and how to configure it.

## Architecture Overview

Basic Memory follows a **proxy-based authentication architecture** where:

1. **OAuth/Authentication happens in a proxy layer** (e.g., Supabase Auth, Auth0, Keycloak)
2. **Basic Memory validates JWTs** issued by the proxy
3. **Tenant isolation** is enforced through JWT claims

```
[Client] → [OAuth Proxy/Auth Server] → [JWT with tenant claims] → [Basic Memory Instance]
                                                                          ↓
                                                                  [FastMCP JWT validation]
                                                                          ↓
                                                                  [Tenant middleware validation]
                                                                          ↓
                                                                  [MCP endpoints]
```

## Authentication Flow

### 1. JWT Signature Validation
- **FastMCP's BearerAuthProvider** validates JWT signatures using JWKS (JSON Web Key Set)
- Verifies the JWT was issued by the trusted authentication server
- Checks token expiration and standard JWT claims

### 2. Tenant Validation 
- **TenantValidationMiddleware** extracts and validates tenant claims
- Ensures the JWT contains the correct `tenant_id` for this Basic Memory instance
- Prevents cross-tenant data access (zero-trust security)

### 3. Request Processing
- If both validations pass, the request proceeds to MCP endpoints
- User context (user ID, tenant ID, role, email) is available from JWT claims

## Environment Variables

### Required for JWT Authentication

```bash
# Enable authentication
FASTMCP_AUTH_ENABLED=true

# JWT validation configuration
FASTMCP_AUTH_JWKS_URI=https://your-auth-server.com/.well-known/jwks.json
FASTMCP_AUTH_ISSUER=https://your-auth-server.com

# Tenant isolation (optional but recommended for multi-tenant)
BASIC_MEMORY_TENANT_ID=your-tenant-id
```

### Environment Variable Details

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `FASTMCP_AUTH_ENABLED` | No | Enable/disable authentication | `true` or `false` (default: `false`) |
| `FASTMCP_AUTH_JWKS_URI` | Yes* | JWKS endpoint for JWT verification | `https://auth.supabase.co/rest/v1/auth/jwks` |
| `FASTMCP_AUTH_ISSUER` | Yes* | Expected JWT issuer | `https://auth.supabase.co/auth/v1` |
| `BASIC_MEMORY_TENANT_ID` | No | Expected tenant ID for this instance | `tenant-123` |

*Required when `FASTMCP_AUTH_ENABLED=true`

## JWT Requirements

Basic Memory expects JWTs with the following structure:

### Required Claims
```json
{
  "iss": "https://your-auth-server.com",  // Must match FASTMCP_AUTH_ISSUER
  "aud": "basic-memory-mcp",              // Fixed audience
  "sub": "user-id-123",                   // User identifier
  "exp": 1672531200,                      // Expiration timestamp
  "iat": 1672444800                       // Issued at timestamp
}
```

### Recommended Claims (for tenant isolation)
```json
{
  "tenant_id": "tenant-123",    // Must match BASIC_MEMORY_TENANT_ID
  "user_role": "admin",         // User role within tenant
  "email": "user@example.com"   // User email
}
```

### Example Complete JWT Payload
```json
{
  "iss": "https://auth.supabase.co/auth/v1",
  "aud": "basic-memory-mcp",
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "acme-corp",
  "user_role": "admin",
  "email": "admin@acme-corp.com",
  "exp": 1672531200,
  "iat": 1672444800
}
```

## Configuration Examples

### Single Tenant Deployment
```bash
# Disable authentication for development/single-user
FASTMCP_AUTH_ENABLED=false
```

### Multi-Tenant with Supabase
```bash
# Enable JWT validation with Supabase
FASTMCP_AUTH_ENABLED=true
FASTMCP_AUTH_JWKS_URI=https://your-project.supabase.co/rest/v1/auth/jwks
FASTMCP_AUTH_ISSUER=https://your-project.supabase.co/auth/v1
BASIC_MEMORY_TENANT_ID=tenant-123
```

### Multi-Tenant with Auth0
```bash
# Enable JWT validation with Auth0
FASTMCP_AUTH_ENABLED=true
FASTMCP_AUTH_JWKS_URI=https://your-domain.auth0.com/.well-known/jwks.json
FASTMCP_AUTH_ISSUER=https://your-domain.auth0.com/
BASIC_MEMORY_TENANT_ID=tenant-123
```

### Multi-Tenant with Keycloak
```bash
# Enable JWT validation with Keycloak
FASTMCP_AUTH_ENABLED=true
FASTMCP_AUTH_JWKS_URI=https://keycloak.example.com/realms/basic-memory/protocol/openid-connect/certs
FASTMCP_AUTH_ISSUER=https://keycloak.example.com/realms/basic-memory
BASIC_MEMORY_TENANT_ID=tenant-123
```

## Security Features

### Zero-Trust Tenant Isolation
- Each Basic Memory instance is configured for a specific tenant
- JWTs must contain the exact `tenant_id` claim matching the instance
- Cross-tenant access is automatically blocked
- No shared data between tenants

### JWT Signature Verification
- All JWTs are cryptographically verified using JWKS
- Tampered or invalid tokens are rejected
- Expired tokens are automatically rejected

### Request Authorization
- Every MCP request must include a valid `Authorization: Bearer <jwt>` header
- Requests without valid JWTs are rejected with HTTP 401
- Cross-tenant requests are rejected with HTTP 403

## Testing

### Local Development
For local development without authentication:
```bash
# Disable authentication
FASTMCP_AUTH_ENABLED=false

# Start Basic Memory
basic-memory mcp --transport streamable-http
```

### With Authentication
For testing with JWT validation:
```bash
# Configure authentication
export FASTMCP_AUTH_ENABLED=true
export FASTMCP_AUTH_JWKS_URI=https://your-auth.com/jwks
export FASTMCP_AUTH_ISSUER=https://your-auth.com
export BASIC_MEMORY_TENANT_ID=test-tenant

# Start Basic Memory
basic-memory mcp --transport streamable-http

# Test with curl (replace <JWT> with actual token)
curl -H "Authorization: Bearer <JWT>" \
     http://localhost:8000/mcp/tools
```

## Troubleshooting

### Authentication Disabled Warning
```
FASTMCP_AUTH_JWKS_URI and FASTMCP_AUTH_ISSUER not configured - authentication disabled
```
**Solution:** Set both `FASTMCP_AUTH_JWKS_URI` and `FASTMCP_AUTH_ISSUER` when `FASTMCP_AUTH_ENABLED=true`

### JWT Validation Failures
```
Invalid JWT token
```
**Solutions:**
- Verify JWT is not expired
- Check JWT signature with JWKS endpoint
- Ensure JWT issuer matches `FASTMCP_AUTH_ISSUER`

### Tenant Validation Failures
```
Access denied: invalid tenant
```
**Solutions:**
- Verify JWT contains `tenant_id` claim
- Check `tenant_id` matches `BASIC_MEMORY_TENANT_ID`
- Ensure tenant ID is correctly set in your auth server

### Missing Authorization Header
```
Missing Authorization header
```
**Solution:** Include `Authorization: Bearer <jwt>` header in all requests

## Migration from OAuth Provider

Basic Memory v0.13+ removed the built-in OAuth provider functionality. If upgrading from an earlier version:

1. **Remove OAuth environment variables:**
   - `FASTMCP_AUTH_PROVIDER`
   - `FASTMCP_AUTH_SECRET_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`

2. **Add JWT validation variables:**
   - `FASTMCP_AUTH_JWKS_URI`
   - `FASTMCP_AUTH_ISSUER`

3. **Update client applications** to obtain JWTs from your external auth provider instead of Basic Memory's OAuth endpoints

4. **Configure tenant isolation** with `BASIC_MEMORY_TENANT_ID` for multi-tenant deployments