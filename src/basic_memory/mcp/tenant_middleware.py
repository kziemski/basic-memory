"""Tenant validation middleware for zero-trust multi-tenant security.

This middleware ensures that JWTs contain the correct tenant_id claim
that matches the tenant instance, preventing cross-tenant data access.
"""

import os
import jwt
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from loguru import logger


class TenantValidationMiddleware(BaseHTTPMiddleware):
    """Starlette middleware for tenant validation."""
    
    def __init__(self, app, tenant_id: Optional[str] = None):
        super().__init__(app)
        self.tenant_id = tenant_id or os.getenv("BASIC_MEMORY_TENANT_ID")
        
        if not self.tenant_id:
            logger.warning("No BASIC_MEMORY_TENANT_ID configured - tenant validation disabled")
        else:
            logger.info(f"Tenant validation enabled for tenant: {self.tenant_id}")
    
    async def dispatch(self, request: Request, call_next):
        logger.info(f"TenantValidationMiddleware: Processing request to {request.url.path}")
        
        # Skip tenant validation if auth is disabled or no tenant ID configured
        if (not os.getenv("FASTMCP_AUTH_ENABLED", "").lower() == "true" or 
            not self.tenant_id):
            logger.info(f"TenantValidationMiddleware: Skipping - auth_enabled={os.getenv('FASTMCP_AUTH_ENABLED')}, tenant_id={self.tenant_id}")
            return await call_next(request)
        
        # Only validate MCP endpoints
        if not request.url.path.startswith("/mcp"):
            logger.info(f"TenantValidationMiddleware: Skipping - not an MCP endpoint")
            return await call_next(request)
        
        try:
            # Extract and validate JWT tenant claims
            token = self._extract_jwt_from_request(request)
            logger.info(f"TenantValidationMiddleware: Extracted token: {'Present' if token else 'Missing'}")
            if token:
                logger.debug(f"TenantValidationMiddleware: Token (first 50 chars): {token[:50]}...")
            
            if not token:
                logger.warning("TenantValidationMiddleware: No Authorization header found")
                return JSONResponse(
                    {"error": "Missing Authorization header"}, 
                    status_code=401
                )
            
            claims = self._decode_jwt_claims(token)
            logger.info(f"TenantValidationMiddleware: Decoded claims: {claims}")
            
            if not claims:
                logger.warning("TenantValidationMiddleware: Failed to decode JWT claims")
                return JSONResponse(
                    {"error": "Invalid JWT format"}, 
                    status_code=401
                )
            
            if not self._validate_tenant_access(claims):
                logger.warning(f"TenantValidationMiddleware: Tenant validation failed for claims: {claims}")
                return JSONResponse(
                    {"error": "Access denied: invalid tenant"}, 
                    status_code=403
                )
            
            logger.info("TenantValidationMiddleware: Validation successful, proceeding to next handler")
            # Continue to next middleware/handler
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"TenantValidationMiddleware: Exception during validation: {e}")
            import traceback
            logger.error(f"TenantValidationMiddleware: Traceback: {traceback.format_exc()}")
            return JSONResponse(
                {"error": "Authentication error"}, 
                status_code=500
            )
    
    def _extract_jwt_from_request(self, request: Request) -> Optional[str]:
        """Extract JWT token from Authorization header."""
        logger.debug(f"TenantValidationMiddleware: All request headers: {dict(request.headers)}")
        auth_header = request.headers.get("authorization", "")
        logger.debug(f"TenantValidationMiddleware: Authorization header: {auth_header[:100] if auth_header else 'None'}...")
        
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            logger.debug(f"TenantValidationMiddleware: Extracted Bearer token (length: {len(token)})")
            return token
        else:
            logger.warning(f"TenantValidationMiddleware: Authorization header doesn't start with 'Bearer ': {auth_header[:50]}...")
            return None
    
    def _decode_jwt_claims(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode JWT claims without signature verification (already done by FastMCP)."""
        try:
            logger.debug(f"TenantValidationMiddleware: Decoding JWT token (length: {len(token)})")
            # Decode without verification since FastMCP already verified signature
            payload = jwt.decode(
                token, options={"verify_signature": False}, algorithms=["RS256", "HS256"]
            )
            logger.debug(f"TenantValidationMiddleware: Successfully decoded JWT payload: {payload}")
            return payload
        except Exception as e:
            logger.error(f"TenantValidationMiddleware: Failed to decode JWT claims: {e}")
            logger.debug(f"TenantValidationMiddleware: Problematic token: {token[:100]}...")
            return None
    
    def _validate_tenant_access(self, claims: Dict[str, Any]) -> bool:
        """Validate that the JWT contains the correct tenant claim."""
        logger.info(f"TenantValidationMiddleware: Validating tenant access")
        logger.info(f"TenantValidationMiddleware: Expected tenant_id: {self.tenant_id}")
        logger.info(f"TenantValidationMiddleware: Available claims: {list(claims.keys())}")
        
        jwt_tenant_id = claims.get("tenant_id")
        logger.info(f"TenantValidationMiddleware: JWT tenant_id claim: {jwt_tenant_id}")
        
        if not jwt_tenant_id:
            logger.warning("TenantValidationMiddleware: JWT missing tenant_id claim")
            logger.info(f"TenantValidationMiddleware: Available claims for debugging: {claims}")
            return False
        
        if jwt_tenant_id != self.tenant_id:
            logger.warning(
                f"TenantValidationMiddleware: Tenant access denied. Expected: {self.tenant_id}, "
                f"Got: {jwt_tenant_id}"
            )
            return False
        
        logger.info(f"TenantValidationMiddleware: Tenant validation successful for: {self.tenant_id}")
        return True
