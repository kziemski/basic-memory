"""
Basic Memory FastMCP server.
"""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Any

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.utilities.logging import configure_logging as mcp_configure_logging
from mcp.server.auth.settings import AuthSettings

from basic_memory.config import app_config
from basic_memory.services.initialization import initialize_app
from basic_memory.mcp.project_session import session

# mcp console logging
mcp_configure_logging(level="ERROR")

load_dotenv()


@dataclass
class AppContext:
    watch_task: Optional[asyncio.Task]
    migration_manager: Optional[Any] = None


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:  # pragma: no cover
    """Manage application lifecycle with type-safe context"""
    # Initialize on startup (now returns migration_manager)
    migration_manager = await initialize_app(app_config)

    # Initialize project session with default project
    session.initialize(app_config.default_project)

    try:
        yield AppContext(watch_task=None, migration_manager=migration_manager)
    finally:
        # Cleanup on shutdown - migration tasks will be cancelled automatically
        pass


# JWT validation configuration function
def create_auth_config() -> tuple[AuthSettings | None, Any | None]:
    """Create JWT validation configuration if enabled."""
    import os

    if os.getenv("FASTMCP_AUTH_ENABLED", "false").lower() == "true":
        # Only support JWT validation, no OAuth provider endpoints
        from fastmcp.server.auth import BearerAuthProvider
        from basic_memory.mcp.tenant_middleware import create_tenant_middleware

        # Get JWT validation configuration
        jwks_uri = os.getenv("FASTMCP_AUTH_JWKS_URI")
        issuer = os.getenv("FASTMCP_AUTH_ISSUER")

        if not jwks_uri or not issuer:
            from loguru import logger

            logger.warning(
                "FASTMCP_AUTH_JWKS_URI and FASTMCP_AUTH_ISSUER not configured - "
                "authentication disabled"
            )
            return None, None

        # Create FastMCP Bearer auth provider for JWT validation
        bearer_auth_provider = BearerAuthProvider(
            jwks_uri=jwks_uri, issuer=issuer, audience="basic-memory-mcp"
        )

        # Add tenant validation middleware
        tenant_middleware = create_tenant_middleware()

        # Combine JWT validation with tenant validation
        class JWTValidatorWithTenant:
            """Combines FastMCP JWT validation with tenant validation."""

            def __init__(self, bearer_auth, tenant_validator):
                self.bearer_auth = bearer_auth
                self.tenant_validator = tenant_validator

            async def __call__(self, request):
                # First: FastMCP validates JWT signature via JWKS
                await self.bearer_auth(request)

                # Second: Validate tenant claims
                user_context = await self.tenant_validator(request)
                return user_context

        combined_auth = JWTValidatorWithTenant(bearer_auth_provider, tenant_middleware)
        return None, combined_auth

    return None, None


# Create auth configuration
auth_settings, auth_provider = create_auth_config()

# Create the shared server instance
mcp = FastMCP(
    name="Basic Memory",
    log_level="DEBUG",
    auth=auth_provider,
)
