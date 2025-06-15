"""Tenant validation middleware for zero-trust multi-tenant security.

This middleware ensures that JWTs contain the correct tenant_id claim
that matches the tenant instance, preventing cross-tenant data access.
"""

import os
import jwt
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException
from loguru import logger


class TenantValidationMiddleware:
    """Middleware to validate JWT tenant claims for zero-trust architecture.

    After FastMCP validates the JWT signature, this middleware ensures
    the tenant_id claim matches the instance's configured tenant ID.
    """

    def __init__(self, tenant_id: Optional[str] = None):
        """Initialize tenant validation middleware.

        Args:
            tenant_id: Expected tenant ID for this instance.
                      If None, uses BASIC_MEMORY_TENANT_ID env var.
        """
        self.tenant_id = tenant_id or os.getenv("BASIC_MEMORY_TENANT_ID")

        if not self.tenant_id:
            logger.warning("No BASIC_MEMORY_TENANT_ID configured - tenant validation disabled")
        else:
            logger.info(f"Tenant validation enabled for tenant: {self.tenant_id}")

    def extract_jwt_from_request(self, request: Request) -> Optional[str]:
        """Extract JWT token from Authorization header.

        Args:
            request: FastAPI request object

        Returns:
            JWT token string if found, None otherwise
        """
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return None

        if not auth_header.startswith("Bearer "):
            return None

        return auth_header[7:]  # Remove "Bearer " prefix

    def decode_jwt_claims(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode JWT claims without signature verification.

        FastMCP already verified the signature, we just need the claims.

        Args:
            token: JWT token string

        Returns:
            JWT payload dict if valid, None if decode fails
        """
        try:
            # Decode without verification since FastMCP already verified signature
            payload = jwt.decode(
                token, options={"verify_signature": False}, algorithms=["RS256", "HS256"]
            )
            return payload
        except Exception as e:
            logger.warning(f"Failed to decode JWT claims: {e}")
            return None

    def validate_tenant_access(self, jwt_payload: Dict[str, Any]) -> bool:
        """Validate that JWT contains correct tenant_id claim.

        Args:
            jwt_payload: Decoded JWT payload

        Returns:
            True if tenant access is valid, False otherwise
        """
        if not self.tenant_id:
            # No tenant validation configured
            return True

        jwt_tenant_id = jwt_payload.get("tenant_id")

        if not jwt_tenant_id:
            logger.warning("JWT missing tenant_id claim")
            return False

        if jwt_tenant_id != self.tenant_id:
            logger.warning(
                f"Tenant ID mismatch: JWT has '{jwt_tenant_id}', expected '{self.tenant_id}'"
            )
            return False

        logger.debug(f"Tenant validation successful for: {self.tenant_id}")
        return True

    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        """Validate tenant access for the request.

        This should be called after FastMCP validates the JWT signature.

        Args:
            request: FastAPI request object

        Returns:
            User context with tenant info if valid

        Raises:
            HTTPException: If tenant validation fails
        """
        # Extract JWT from request
        token = self.extract_jwt_from_request(request)
        if not token:
            if self.tenant_id:
                # Tenant validation is enabled but no token provided
                raise HTTPException(status_code=401, detail="Missing Authorization header")
            else:
                # No tenant validation configured
                return {"tenant_validation": "disabled"}

        # Decode JWT claims
        jwt_payload = self.decode_jwt_claims(token)
        if not jwt_payload:
            raise HTTPException(status_code=401, detail="Invalid JWT token")

        # Validate tenant access
        if not self.validate_tenant_access(jwt_payload):
            raise HTTPException(status_code=403, detail="Access denied: invalid tenant")

        # Return user context with tenant information
        return {
            "user_id": jwt_payload.get("sub"),
            "tenant_id": jwt_payload.get("tenant_id"),
            "user_role": jwt_payload.get("user_role"),
            "email": jwt_payload.get("email"),
            "tenant_validation": "passed",
        }


def create_tenant_middleware() -> TenantValidationMiddleware:
    """Factory function to create tenant validation middleware."""
    return TenantValidationMiddleware()
