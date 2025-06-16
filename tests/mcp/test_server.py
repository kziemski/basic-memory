"""Tests for MCP server configuration."""

import os
from unittest.mock import patch

from basic_memory.mcp.server import create_auth_config


class TestMCPServer:
    """Test MCP server configuration."""

    def test_create_auth_config_disabled(self):
        """Test auth config creation when authentication is disabled."""
        with patch.dict(os.environ, {}, clear=True):
            auth_settings, auth_provider = create_auth_config()
            assert auth_settings is None
            assert auth_provider is None

    def test_create_auth_config_enabled_missing_jwks_uri(self):
        """Test auth config creation with authentication enabled but missing JWKS URI."""
        env_vars = {
            "FASTMCP_AUTH_ENABLED": "true",
            "FASTMCP_AUTH_ISSUER": "https://example.supabase.co/auth/v1",
            # Missing FASTMCP_AUTH_JWKS_URI
        }

        with patch.dict(os.environ, env_vars, clear=True):
            auth_settings, auth_provider = create_auth_config()
            assert auth_settings is None
            assert auth_provider is None

    def test_create_auth_config_enabled_missing_issuer(self):
        """Test auth config creation with authentication enabled but missing issuer."""
        env_vars = {
            "FASTMCP_AUTH_ENABLED": "true",
            "FASTMCP_AUTH_JWKS_URI": "https://example.supabase.co/rest/v1/auth/jwks",
            # Missing FASTMCP_AUTH_ISSUER
        }

        with patch.dict(os.environ, env_vars, clear=True):
            auth_settings, auth_provider = create_auth_config()
            assert auth_settings is None
            assert auth_provider is None

    def test_create_auth_config_enabled_with_jwt_validation(self):
        """Test auth config creation with complete JWT validation configuration."""
        env_vars = {
            "FASTMCP_AUTH_ENABLED": "true",
            "FASTMCP_AUTH_JWKS_URI": "https://example.supabase.co/rest/v1/auth/jwks",
            "FASTMCP_AUTH_ISSUER": "https://example.supabase.co/auth/v1",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            auth_settings, auth_provider = create_auth_config()

            # JWT validation doesn't need OAuth settings
            assert auth_settings is None

            # Should have a BearerAuthProvider (tenant validation is in middleware)
            assert auth_provider is not None
            assert auth_provider.__class__.__name__ == "BearerAuthProvider"

    def test_create_auth_config_disabled_explicitly(self):
        """Test auth config creation when explicitly disabled."""
        env_vars = {
            "FASTMCP_AUTH_ENABLED": "false",
            "FASTMCP_AUTH_JWKS_URI": "https://example.supabase.co/rest/v1/auth/jwks",
            "FASTMCP_AUTH_ISSUER": "https://example.supabase.co/auth/v1",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            auth_settings, auth_provider = create_auth_config()
            assert auth_settings is None
            assert auth_provider is None
