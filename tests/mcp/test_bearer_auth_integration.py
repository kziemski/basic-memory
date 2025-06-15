"""Tests for JWT validation integration."""

import os
from unittest.mock import patch

from basic_memory.mcp.server import create_auth_config


def test_jwt_validation_requires_jwks_uri_and_issuer():
    """Test that JWT validation requires JWKS URI and issuer."""
    with patch.dict(
        os.environ,
        {
            "FASTMCP_AUTH_ENABLED": "true",
        },
        clear=True,
    ):
        # Should return None when JWKS URI and issuer are missing
        auth_settings, auth_provider = create_auth_config()
        assert auth_settings is None
        assert auth_provider is None


def test_jwt_validation_with_jwks_uri_and_issuer():
    """Test successful JWT validation configuration with JWKS URI and issuer."""
    with patch.dict(
        os.environ,
        {
            "FASTMCP_AUTH_ENABLED": "true",
            "FASTMCP_AUTH_JWKS_URI": "https://example.supabase.co/rest/v1/auth/jwks",
            "FASTMCP_AUTH_ISSUER": "https://example.supabase.co/auth/v1",
        },
        clear=True,
    ):
        auth_settings, auth_provider = create_auth_config()

        # JWT validation returns None for auth_settings (no OAuth endpoints)
        assert auth_settings is None

        # Should have a JWTValidatorWithTenant
        assert auth_provider is not None
        assert auth_provider.__class__.__name__ == "JWTValidatorWithTenant"


def test_auth_disabled():
    """Test that authentication can be disabled."""
    with patch.dict(os.environ, {"FASTMCP_AUTH_ENABLED": "false"}, clear=True):
        auth_settings, auth_provider = create_auth_config()

        assert auth_settings is None
        assert auth_provider is None


def test_missing_jwks_uri_only():
    """Test missing only JWKS URI."""
    with patch.dict(
        os.environ,
        {
            "FASTMCP_AUTH_ENABLED": "true",
            "FASTMCP_AUTH_ISSUER": "https://example.supabase.co/auth/v1",
        },
        clear=True,
    ):
        auth_settings, auth_provider = create_auth_config()
        assert auth_settings is None
        assert auth_provider is None


def test_missing_issuer_only():
    """Test missing only issuer."""
    with patch.dict(
        os.environ,
        {
            "FASTMCP_AUTH_ENABLED": "true",
            "FASTMCP_AUTH_JWKS_URI": "https://example.supabase.co/rest/v1/auth/jwks",
        },
        clear=True,
    ):
        auth_settings, auth_provider = create_auth_config()
        assert auth_settings is None
        assert auth_provider is None
