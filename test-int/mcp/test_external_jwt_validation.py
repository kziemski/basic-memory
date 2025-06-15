"""
Integration tests for JWT validation with external tokens.

These tests verify that Basic Memory can validate JWTs issued by external
OAuth servers (like a proxy layer) without needing to be an OAuth provider itself.
"""

import jwt
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from basic_memory.mcp.tenant_middleware import TenantValidationMiddleware


def create_external_jwt(
    tenant_id: str = "tenant-123",
    user_id: str = "user-456",
    issuer: str = "https://proxy.example.com/auth",
) -> str:
    """Create a JWT as if it came from an external OAuth server/proxy."""
    payload = {
        "iss": issuer,  # External issuer
        "aud": "basic-memory-mcp",
        "sub": user_id,
        "tenant_id": tenant_id,
        "user_role": "admin",
        "email": "test@example.com",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }

    # Sign with a test secret (in production, this would be signed by the proxy)
    return jwt.encode(payload, "proxy-secret", algorithm="HS256")


@pytest.mark.asyncio
async def test_external_jwt_validation_success():
    """Test that tenant middleware can validate external JWTs successfully."""
    # Create tenant middleware for a specific tenant
    middleware = TenantValidationMiddleware(tenant_id="tenant-123")

    # Create a JWT as if it came from an external OAuth server
    external_jwt = create_external_jwt(tenant_id="tenant-123", user_id="external-user-789")

    # Create mock request with the external JWT
    request = Mock()
    request.headers = {"authorization": f"Bearer {external_jwt}"}

    # This should successfully validate the tenant claims
    result = await middleware(request)

    assert result is not None
    assert result["user_id"] == "external-user-789"
    assert result["tenant_id"] == "tenant-123"
    assert result["user_role"] == "admin"
    assert result["email"] == "test@example.com"
    assert result["tenant_validation"] == "passed"


@pytest.mark.asyncio
async def test_external_jwt_cross_tenant_prevention():
    """Test that cross-tenant access is prevented with external JWTs."""
    # Create tenant middleware for tenant-123
    middleware = TenantValidationMiddleware(tenant_id="tenant-123")

    # Create JWT for a different tenant (as if from external server)
    external_jwt = create_external_jwt(tenant_id="tenant-456", user_id="user-789")

    request = Mock()
    request.headers = {"authorization": f"Bearer {external_jwt}"}

    # Should raise HTTPException for cross-tenant access
    with pytest.raises(Exception) as exc_info:
        await middleware(request)

    assert "invalid tenant" in str(exc_info.value)


@pytest.mark.asyncio
async def test_external_jwt_different_issuers():
    """Test that JWTs from different external issuers work (issuer doesn't matter for tenant validation)."""
    middleware = TenantValidationMiddleware(tenant_id="tenant-123")

    # Test with different external issuers
    issuers = [
        "https://auth.supabase.co",
        "https://oauth-proxy.example.com",
        "https://keycloak.company.com/realms/basic-memory",
    ]

    for issuer in issuers:
        external_jwt = create_external_jwt(
            tenant_id="tenant-123",
            user_id=f"user-{issuer.split('//')[1].split('.')[0]}",
            issuer=issuer,
        )

        request = Mock()
        request.headers = {"authorization": f"Bearer {external_jwt}"}

        result = await middleware(request)

        assert result is not None
        assert result["tenant_id"] == "tenant-123"
        assert result["tenant_validation"] == "passed"


@pytest.mark.asyncio
async def test_external_jwt_missing_tenant_claim():
    """Test that external JWTs without tenant_id claim are rejected."""
    middleware = TenantValidationMiddleware(tenant_id="tenant-123")

    # Create JWT without tenant_id claim
    payload = {
        "iss": "https://proxy.example.com/auth",
        "aud": "basic-memory-mcp",
        "sub": "user-456",
        "user_role": "admin",
        "email": "test@example.com",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        # Missing tenant_id
    }
    external_jwt = jwt.encode(payload, "proxy-secret", algorithm="HS256")

    request = Mock()
    request.headers = {"authorization": f"Bearer {external_jwt}"}

    with pytest.raises(Exception) as exc_info:
        await middleware(request)

    assert exc_info.value.status_code == 403


def test_decode_external_jwt_without_verification():
    """Test that external JWTs can be decoded without signature verification."""
    external_jwt = create_external_jwt(tenant_id="test-tenant", user_id="test-user")

    # Decode without verification (signature already verified by FastMCP layer)
    payload = jwt.decode(external_jwt, options={"verify_signature": False})

    assert payload["tenant_id"] == "test-tenant"
    assert payload["sub"] == "test-user"
    assert payload["iss"] == "https://proxy.example.com/auth"
    assert payload["aud"] == "basic-memory-mcp"


@pytest.mark.asyncio
async def test_tenant_validation_disabled_with_external_jwt():
    """Test that when tenant validation is disabled, external JWTs still work."""
    # Create middleware without tenant validation
    middleware = TenantValidationMiddleware(tenant_id=None)

    external_jwt = create_external_jwt(tenant_id="any-tenant", user_id="any-user")

    request = Mock()
    request.headers = {"authorization": f"Bearer {external_jwt}"}

    result = await middleware(request)

    assert result is not None
    assert result["user_id"] == "any-user"
    assert result["tenant_id"] == "any-tenant"
    assert result["tenant_validation"] == "passed"  # Still extracts info but doesn't validate


@pytest.mark.asyncio
async def test_external_jwt_with_custom_claims():
    """Test that external JWTs with custom claims are handled properly."""
    middleware = TenantValidationMiddleware(tenant_id="tenant-123")

    # Create JWT with additional custom claims
    payload = {
        "iss": "https://proxy.example.com/auth",
        "aud": "basic-memory-mcp",
        "sub": "user-456",
        "tenant_id": "tenant-123",
        "user_role": "admin",
        "email": "test@example.com",
        "organization": "Basic Machines",
        "permissions": ["read", "write", "admin"],
        "custom_field": "custom_value",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    external_jwt = jwt.encode(payload, "proxy-secret", algorithm="HS256")

    request = Mock()
    request.headers = {"authorization": f"Bearer {external_jwt}"}

    result = await middleware(request)

    assert result is not None
    assert result["user_id"] == "user-456"
    assert result["tenant_id"] == "tenant-123"
    assert result["user_role"] == "admin"
    assert result["email"] == "test@example.com"
    assert result["tenant_validation"] == "passed"
