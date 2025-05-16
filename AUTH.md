To test the built-in OAuth flow locally, here's what you need to do:

1. Set Environment Variables

  First, create a .env file based on the example:

  cp .env.oauth.example .env

  Then edit .env to enable OAuth:

  # Enable OAuth authentication
  FASTMCP_AUTH_ENABLED=true

  # Use the basic (built-in) provider
  FASTMCP_AUTH_PROVIDER=basic

  # OAuth issuer URL (your MCP server URL)
  FASTMCP_AUTH_ISSUER_URL=http://localhost:8000

2. Start the MCP Server with OAuth

  Start the server using the streamable-http transport (OAuth works best with HTTP):

  # Run with OAuth enabled
  FASTMCP_AUTH_ENABLED=true basic-memory mcp --transport streamable-http

  # Or if you have the env vars in .env file:
  basic-memory mcp --transport streamable-http

  You should see:
  OAuth authentication is ENABLED
  Issuer URL: http://localhost:8000

3. Register an OAuth Client

  In a new terminal, register a test client:

  basic-memory auth register-client

  This will output something like:
  Client registered successfully!
  Client ID: AbCdEfGhIjKlMnOp
  Client Secret: QrStUvWxYz123456789...

  Save these credentials!

4. Test the OAuth Flow

  Run the built-in test command:

  basic-memory auth test-auth

  This will:
1. Register a test client
2. Generate an authorization URL
3. Exchange the auth code for tokens
4. Validate the access token

  You'll see output like:
  Registered test client: ABC123...
  Authorization URL: http://localhost:3000/callback?code=XYZ&state=test-state
  Access token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
  Refresh token: QrStUvWxYz...
  Expires in: 3600 seconds
  Access token validated successfully!

5. Test with a Real Client

  To test with an actual MCP client, you'll need to:

1. Make an authorization request:
  # Use the client_id from step 3
  curl "http://localhost:8000/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:3000/callback&response_type=code&code_challenge=test-challenge&code_challenge_method=S256"

2. Exchange the code for tokens:
  # Use the code from the redirect URL
  curl -X POST http://localhost:8000/token \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=authorization_code&code=YOUR_AUTH_CODE&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET&code_verifier=test-verifier"

3. Use the access token to call MCP endpoints:
curl http://localhost:8000/mcp \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

6. Quick Test Script

  Here's a simple Python script to test the flow:

  import httpx
  import asyncio
  from urllib.parse import urlparse, parse_qs

  async def test_oauth():
      client = httpx.AsyncClient()

      # Your client credentials
      client_id = "YOUR_CLIENT_ID"
      client_secret = "YOUR_CLIENT_SECRET"

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

7. Debug Tips

- Check the server logs for OAuth-related messages
- The basic provider stores everything in memory, so clients/tokens are lost on restart
- You can modify the log level for more details:
FASTMCP_AUTH_ENABLED=true basic-memory mcp --transport streamable-http

  That's it! The built-in OAuth provider is perfect for local development and testing. For production, you'd want to use an external provider (GitHub/Google) or implement persistent storage for the basic provider.