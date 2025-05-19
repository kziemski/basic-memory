#!/usr/bin/env python
"""Test OAuth authentication with MCP server.

Usage:
    1. Start the server with OAuth enabled:
       export FASTMCP_AUTH_SECRET_KEY="test-secret-key"
       FASTMCP_AUTH_ENABLED=true basic-memory mcp --transport streamable-http
    
    2. Get a test token:
       export FASTMCP_AUTH_SECRET_KEY="test-secret-key"
       basic-memory auth test-auth
    
    3. Test the token:
       python test_oauth.py <access_token>
    
    4. Use in MCP Inspector:
       - Server URL: http://localhost:8000/mcp/
       - Transport: streamable-http
       - Custom Headers:
         Authorization: Bearer <access_token>
         Accept: application/json, text/event-stream
"""

import httpx
import asyncio
import sys


async def test_mcp_auth(access_token: str):
    """Test MCP endpoint with OAuth token."""
    
    async with httpx.AsyncClient() as client:
        # Test MCP endpoint with bearer token (note the trailing slash)
        response = await client.post(
            "http://localhost:8000/mcp/",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json, text/event-stream"  # MCP requires both
            },
            follow_redirects=False,  # Don't follow redirects automatically
            json={
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {
                        "sampling": {},
                        "roots": {"listChanged": True}
                    },
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                },
                "jsonrpc": "2.0",
                "id": 0
            }
        )
        
        print(f"Response Status: {response.status_code}")
        if response.status_code == 200:
            print("Success! OAuth authentication working.")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Response body (first 100 chars): {response.text[:100]}")
        else:
            print(f"Error: {response.text}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_oauth.py <access_token>")
        sys.exit(1)
    
    access_token = sys.argv[1]
    asyncio.run(test_mcp_auth(access_token))