# OAuth Quick Start Guide

This guide shows how to test OAuth authentication with Basic Memory MCP server, including how to connect from Claude.ai.

## Local Testing with Built-in Provider

1. **Create `.env` file**:
   ```bash
   cp .env.oauth.example .env
   ```

2. **Enable OAuth** in `.env`:
   ```bash
   FASTMCP_AUTH_ENABLED=true
   FASTMCP_AUTH_PROVIDER=basic
   ```

3. **Start the server**:
   ```bash
   # Using environment variables
   basic-memory mcp --transport streamable-http

   # Or directly
   FASTMCP_AUTH_ENABLED=true basic-memory mcp --transport streamable-http
   ```

4. **Register a client**:
   ```bash
   basic-memory auth register-client
   # Save the client_id and client_secret!
   ```

5. **Test the flow**:
   ```bash
   basic-memory auth test-auth
   ```

## Production with Supabase

1. **Create Supabase project** at [supabase.com](https://supabase.com)

2. **Configure `.env`**:
   ```bash
   FASTMCP_AUTH_ENABLED=true
   FASTMCP_AUTH_PROVIDER=supabase
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-key
   ```

3. **Start the server**:
   ```bash
   basic-memory mcp --transport streamable-http
   ```

## OAuth Endpoints

When OAuth is enabled, these endpoints are available:

- `GET /authorize` - OAuth authorization endpoint
- `POST /token` - Token exchange endpoint
- `GET /mcp` - Protected MCP endpoint (requires Bearer token)

## Testing with cURL

1. **Get authorization code**:
   ```bash
   curl "http://localhost:8000/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:3000/callback&response_type=code&code_challenge=test"
   ```

2. **Exchange for token**:
   ```bash
   curl -X POST http://localhost:8000/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=authorization_code&code=AUTH_CODE&client_id=CLIENT_ID&client_secret=CLIENT_SECRET"
   ```

3. **Use the token**:
   ```bash
   curl http://localhost:8000/mcp \
     -H "Authorization: Bearer ACCESS_TOKEN"
   ```

## Quick Test Script

```python
import httpx
import asyncio
from urllib.parse import urlparse, parse_qs

async def test_oauth():
    # Your client credentials
    client_id = "YOUR_CLIENT_ID"
    client_secret = "YOUR_CLIENT_SECRET"
    
    async with httpx.AsyncClient() as client:
        # 1. Get authorization URL
        auth_response = await client.get(
            "http://localhost:8000/authorize",
            params={
                "client_id": client_id,
                "redirect_uri": "http://localhost:3000/callback",
                "response_type": "code",
                "code_challenge": "test-challenge",
                "code_challenge_method": "S256",
            }
        )
        
        # Extract code from redirect
        redirect_url = auth_response.headers.get("Location")
        parsed = urlparse(redirect_url)
        code = parse_qs(parsed.query)["code"][0]
        
        # 2. Exchange code for tokens
        token_response = await client.post(
            "http://localhost:8000/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "code_verifier": "test-verifier",
            }
        )
        tokens = token_response.json()
        
        # 3. Use access token
        mcp_response = await client.get(
            "http://localhost:8000/mcp",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        
        print(f"MCP Response: {mcp_response.status_code}")

asyncio.run(test_oauth())
```

## Connecting from Claude.ai

To connect your Basic Memory MCP server to Claude.ai:

1. **Deploy your MCP server** with OAuth enabled:
   ```bash
   # Must use streamable-http transport
   FASTMCP_AUTH_ENABLED=true basic-memory mcp --transport streamable-http --host 0.0.0.0
   ```

2. **Make server accessible** (for testing):
   - Use a tunneling service like ngrok: `ngrok http 8000`
   - Or deploy to a cloud provider
   - Note the public URL (e.g., `https://xyz.ngrok.io`)

3. **In Claude.ai**:
   - Go to **Settings** → **Integrations**
   - Click **Add More**
   - Enter your MCP server URL: `https://your-server.com/mcp`
   - Click **Connect**

4. **OAuth Flow**:
   - Claude will redirect you to your MCP server's authorization page
   - Login/authorize (depends on your provider)
   - You'll be redirected back to Claude
   - Claude now has access to your MCP server!

5. **Use in conversation**:
   - Click the tools icon (second from bottom left)
   - Select your Basic Memory server
   - Use commands like "write a note" or "search my notes"

## Provider Options

- **basic**: Built-in provider (development only)
- **supabase**: Supabase Auth (recommended for production)
- **github**: GitHub OAuth
- **google**: Google OAuth

## Debug Tips

- Check server logs for OAuth messages
- Basic provider stores in memory (lost on restart)
- Enable debug logging: `export FASTMCP_LOG_LEVEL=DEBUG`

## Documentation

- [OAuth Authentication Guide](docs/OAuth%20Authentication.md)
- [Supabase OAuth Setup](docs/Supabase%20OAuth%20Setup.md)
- [MCP Authorization Spec](https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization)


## CLAUDE OAUTH

⏺ Summary

  Yes! Basic Memory now supports OAuth authentication that works with Claude.ai, just like claude-code. Here's what I've implemented:

  1. OAuth Flow for Claude.ai

  - Claude initiates the OAuth flow when connecting to your MCP server
  - The server handles authorization, token exchange, and validation
  - Full compliance with MCP OAuth 2.1 specification

  2. Key Components Added

  - OAuth authorization endpoints (/auth/authorize, /auth/token)
  - OAuth metadata discovery (/.well-known/oauth-authorization-server)
  - Support for PKCE (required by Claude)
  - Token refresh and revocation

  3. How to Connect from Claude.ai

  For testing locally:
  # 1. Enable OAuth
  export FASTMCP_AUTH_ENABLED=true

  # 2. Start server
  basic-memory mcp --transport streamable-http --host 0.0.0.0

  # 3. Make it accessible (use ngrok for testing)
  ngrok http 8000

  # 4. In Claude.ai:
  # Settings → Integrations → Add More
  # Enter: https://your-ngrok-url.ngrok.io/mcp
  # Click Connect → Authorize

  4. Production Setup

  - Use Supabase provider for production
  - Deploy to HTTPS (required for OAuth)
  - Claude.ai Enterprise can add for entire organization

  5. Security Features

  - Scoped access (read, write, admin)
  - Short-lived tokens
  - Secure token storage
  - HTTPS required

  The implementation follows the same pattern as claude-code, where:
  1. User adds the MCP server URL in Claude settings
  2. Claude redirects to your authorization endpoint
  3. User logs in and authorizes
  4. Claude receives tokens and can access your MCP tools

  This enables persistent memory and knowledge management directly within Claude.ai conversations!