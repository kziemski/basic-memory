# OAuth Authentication for Basic Memory MCP Server

Basic Memory supports OAuth 2.1 authentication for secure access to the MCP server. This guide explains how to configure and use OAuth authentication.

## Overview

OAuth support in Basic Memory includes:
- Built-in OAuth provider with in-memory storage
- Integration with external OAuth providers (GitHub, Google)
- OAuth client management via CLI
- Support for PKCE (Proof Key for Code Exchange)
- Token validation and revocation

## Configuration

### Environment Variables

Copy `.env.oauth.example` to `.env` and configure:

```bash
# Enable OAuth authentication
FASTMCP_AUTH_ENABLED=true

# OAuth provider type: basic, github, or google
FASTMCP_AUTH_PROVIDER=basic

# OAuth issuer URL (your MCP server URL)
FASTMCP_AUTH_ISSUER_URL=http://localhost:8000

# Required scopes (comma-separated)
FASTMCP_AUTH_REQUIRED_SCOPES=read,write
```

### Provider Types

1. **Basic Provider** (default)
   - Built-in OAuth implementation
   - In-memory storage (not suitable for production)
   - Good for development and testing

2. **GitHub Provider**
   - Integrates with GitHub OAuth
   - Requires GitHub OAuth app configuration
   - Set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`

3. **Google Provider**
   - Integrates with Google OAuth
   - Requires Google OAuth app configuration  
   - Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`

## Usage

### Start the MCP Server with OAuth

```bash
# Start with OAuth enabled
FASTMCP_AUTH_ENABLED=true bm mcp

# Check OAuth status
# The server will display:
# "OAuth authentication is ENABLED"
# "Issuer URL: http://localhost:8000"
```

### Managing OAuth Clients

Register a new OAuth client:

```bash
# Auto-generate client credentials
bm auth register-client

# Specify custom client ID
bm auth register-client --client-id my-client-id
```

Test the OAuth flow:

```bash
bm auth test-auth
```

### OAuth Flow

1. **Authorization Request**
   ```
   GET /authorize?client_id=xxx&redirect_uri=xxx&response_type=code&state=xxx&code_challenge=xxx
   ```

2. **Token Exchange**
   ```
   POST /token
   Content-Type: application/x-www-form-urlencoded
   
   grant_type=authorization_code&code=xxx&client_id=xxx&client_secret=xxx
   ```

3. **Access Protected Resources**
   ```
   GET /mcp
   Authorization: Bearer <access_token>
   ```

4. **Refresh Token**
   ```
   POST /token
   grant_type=refresh_token&refresh_token=xxx&client_id=xxx&client_secret=xxx
   ```

## HTTP Transport with OAuth

When using streamable-http transport with OAuth:

```bash
# Start server with OAuth
FASTMCP_AUTH_ENABLED=true bm mcp --transport streamable-http --host 0.0.0.0 --port 8000

# The server provides these endpoints:
# - /authorize - OAuth authorization
# - /token - Token exchange
# - /mcp - Protected MCP endpoint
```

## Security Considerations

1. **HTTPS Required**: Always use HTTPS in production
2. **Secret Storage**: Store client secrets securely
3. **Token Expiration**: Access tokens expire after 1 hour
4. **Scope Validation**: Configure required scopes appropriately
5. **PKCE**: Always use PKCE for enhanced security

## External Provider Setup

### GitHub OAuth

1. Create a GitHub OAuth App:
   - Go to GitHub Settings > Developer settings > OAuth Apps
   - Create new OAuth App
   - Set Authorization callback URL to `http://localhost:8000/callback`

2. Configure environment:
   ```bash
   FASTMCP_AUTH_PROVIDER=github
   GITHUB_CLIENT_ID=your-client-id
   GITHUB_CLIENT_SECRET=your-client-secret
   ```

### Google OAuth

1. Create Google OAuth credentials:
   - Go to Google Cloud Console
   - Create OAuth 2.0 Client ID
   - Add redirect URI: `http://localhost:8000/callback`

2. Configure environment:
   ```bash
   FASTMCP_AUTH_PROVIDER=google
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

## Development

For development, use the basic provider with test clients:

```bash
# Enable OAuth with basic provider
FASTMCP_AUTH_ENABLED=true FASTMCP_AUTH_PROVIDER=basic bm mcp

# Register test client
bm auth register-client

# Test the flow
bm auth test-auth
```

## Troubleshooting

- **401 Unauthorized**: Check token validity and expiration
- **403 Forbidden**: Verify required scopes are present
- **Invalid client**: Ensure client credentials are correct
- **Token expired**: Use refresh token to get new access token

## API Reference

See the MCP Authorization specification:
https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization