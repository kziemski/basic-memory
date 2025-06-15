"""Tests for tenant validation middleware."""

import os
import jwt
import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException

from basic_memory.mcp.tenant_middleware import TenantValidationMiddleware


def create_test_jwt(tenant_id: str = "tenant-123", user_id: str = "user-456") -> str:
    """Create a test JWT with tenant claims."""
    payload = {
        "iss": "https://test-project.supabase.co",
        "aud": "basic-memory-mcp",
        "sub": user_id,
        "tenant_id": tenant_id,
        "user_role": "admin",
        "email": "test@example.com",
        "exp": 9999999999,  # Far future
    }

    # Use HS256 for testing (easier than RS256)
    return jwt.encode(payload, "test-secret", algorithm="HS256")


@pytest.fixture
def tenant_middleware():
    """Create tenant middleware for testing."""
    return TenantValidationMiddleware(tenant_id="tenant-123")


@pytest.fixture
def mock_request_with_jwt():
    """Create mock request with JWT."""

    def _create_request(token: str):
        request = Mock()
        request.headers = {"authorization": f"Bearer {token}"}
        return request

    return _create_request


@pytest.fixture
def mock_request_no_auth():
    """Create mock request without auth header."""
    request = Mock()
    request.headers = {}
    return request


@pytest.mark.asyncio
async def test_valid_tenant_access(tenant_middleware, mock_request_with_jwt):
    """Test successful tenant validation with matching tenant ID."""
    token = create_test_jwt(tenant_id="tenant-123")
    request = mock_request_with_jwt(token)

    result = await tenant_middleware(request)

    assert result is not None
    assert result["user_id"] == "user-456"
    assert result["tenant_id"] == "tenant-123"
    assert result["user_role"] == "admin"
    assert result["email"] == "test@example.com"
    assert result["tenant_validation"] == "passed"


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(tenant_middleware, mock_request_with_jwt):
    """Test that cross-tenant access is denied."""
    # JWT for different tenant
    token = create_test_jwt(tenant_id="tenant-456")  # Different from middleware's tenant-123
    request = mock_request_with_jwt(token)

    with pytest.raises(HTTPException) as exc_info:
        await tenant_middleware(request)

    assert exc_info.value.status_code == 403
    assert "invalid tenant" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_missing_tenant_id_in_jwt(tenant_middleware, mock_request_with_jwt):
    """Test JWT without tenant_id claim is rejected."""
    payload = {
        "iss": "https://test-project.supabase.co",
        "aud": "basic-memory-mcp",
        "sub": "user-456",
        "email": "test@example.com",
        # Missing tenant_id
    }
    token = jwt.encode(payload, "test-secret", algorithm="HS256")
    request = mock_request_with_jwt(token)

    with pytest.raises(HTTPException) as exc_info:
        await tenant_middleware(request)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_missing_authorization_header(tenant_middleware, mock_request_no_auth):
    """Test request without Authorization header is rejected."""
    with pytest.raises(HTTPException) as exc_info:
        await tenant_middleware(mock_request_no_auth)

    assert exc_info.value.status_code == 401
    assert "Missing Authorization header" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_invalid_jwt_format(tenant_middleware, mock_request_with_jwt):
    """Test invalid JWT format is rejected."""
    request = mock_request_with_jwt("invalid-jwt-token")

    with pytest.raises(HTTPException) as exc_info:
        await tenant_middleware(request)

    assert exc_info.value.status_code == 401
    assert "Invalid JWT token" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_tenant_validation_disabled():
    """Test middleware when no tenant ID is configured."""
    # Create middleware without tenant_id
    middleware = TenantValidationMiddleware(tenant_id=None)

    # Request without auth header should pass
    request = Mock()
    request.headers = {}

    result = await middleware(request)
    assert result == {"tenant_validation": "disabled"}


@pytest.mark.asyncio
async def test_tenant_validation_disabled_with_jwt():
    """Test middleware with JWT when tenant validation is disabled."""
    middleware = TenantValidationMiddleware(tenant_id=None)

    token = create_test_jwt(tenant_id="any-tenant")
    request = Mock()
    request.headers = {"authorization": f"Bearer {token}"}

    result = await middleware(request)
    # When tenant validation is disabled but JWT is provided,
    # we still extract user context but don't validate tenant
    assert result["user_id"] == "user-456"
    assert result["tenant_id"] == "any-tenant"
    assert result["tenant_validation"] == "passed"


def test_extract_jwt_from_request(tenant_middleware):
    """Test JWT extraction from Authorization header."""
    # Valid Bearer token
    request = Mock()
    request.headers = {"authorization": "Bearer test-token-123"}

    token = tenant_middleware.extract_jwt_from_request(request)
    assert token == "test-token-123"

    # No authorization header
    request.headers = {}
    token = tenant_middleware.extract_jwt_from_request(request)
    assert token is None

    # Wrong format (not Bearer)
    request.headers = {"authorization": "Basic credentials"}
    token = tenant_middleware.extract_jwt_from_request(request)
    assert token is None


def test_decode_jwt_claims(tenant_middleware):
    """Test JWT claims decoding."""
    token = create_test_jwt(tenant_id="test-tenant")

    claims = tenant_middleware.decode_jwt_claims(token)
    assert claims is not None
    assert claims["tenant_id"] == "test-tenant"
    assert claims["sub"] == "user-456"

    # Invalid token
    claims = tenant_middleware.decode_jwt_claims("invalid-token")
    assert claims is None


def test_validate_tenant_access(tenant_middleware):
    """Test tenant access validation logic."""
    # Valid tenant
    payload = {"tenant_id": "tenant-123"}
    assert tenant_middleware.validate_tenant_access(payload) is True

    # Wrong tenant
    payload = {"tenant_id": "tenant-456"}
    assert tenant_middleware.validate_tenant_access(payload) is False

    # Missing tenant_id
    payload = {"sub": "user-123"}
    assert tenant_middleware.validate_tenant_access(payload) is False


def test_create_tenant_middleware_from_env():
    """Test creating middleware from environment variable."""
    with patch.dict(os.environ, {"BASIC_MEMORY_TENANT_ID": "env-tenant-123"}):
        from basic_memory.mcp.tenant_middleware import create_tenant_middleware

        middleware = create_tenant_middleware()
        assert middleware.tenant_id == "env-tenant-123"


def test_middleware_init_without_tenant_id():
    """Test middleware initialization without tenant ID shows warning."""
    with patch.dict(os.environ, {}, clear=True):
        middleware = TenantValidationMiddleware()
        assert middleware.tenant_id is None
