"""MCP server command with streamable HTTP transport."""

import asyncio
import typer
import uvicorn

from basic_memory.cli.app import app

# Import mcp instance
from basic_memory.mcp.server import mcp as mcp_server  # pragma: no cover

# Import mcp tools to register them
import basic_memory.mcp.tools  # noqa: F401  # pragma: no cover

# Import prompts to register them
import basic_memory.mcp.prompts  # noqa: F401  # pragma: no cover
from loguru import logger

@app.command()
def mcp(
    transport: str = typer.Option(
        "stdio", help="Transport type: stdio, streamable-http, or sse"
    ),
    host: str = typer.Option(
        "0.0.0.0", help="Host for HTTP transports (use 0.0.0.0 to allow external connections)"
    ),
    port: int = typer.Option(8000, help="Port for HTTP transports"),
    path: str = typer.Option("/mcp", help="Path prefix for streamable-http transport"),
):  # pragma: no cover
    """Run the MCP server with configurable transport options.

    This command starts an MCP server using one of three transport options:

    - stdio: Standard I/O (good for local usage)
    - streamable-http: Recommended for web deployments (default)
    - sse: Server-Sent Events (for compatibility with existing clients)
    """
    
    # Check if OAuth is enabled
    import os
    auth_enabled = os.getenv("FASTMCP_AUTH_ENABLED", "false").lower() == "true"
    if auth_enabled:
        logger.info("OAuth authentication is ENABLED")
        logger.info(f"Issuer URL: {os.getenv('FASTMCP_AUTH_ISSUER_URL', 'http://localhost:8000')}")
        if os.getenv("FASTMCP_AUTH_REQUIRED_SCOPES"):
            logger.info(f"Required scopes: {os.getenv('FASTMCP_AUTH_REQUIRED_SCOPES')}")
    else:
        logger.info("OAuth authentication is DISABLED")

    from basic_memory.config import app_config
    from basic_memory.services.initialization import initialize_file_sync

    # Start the MCP server with the specified transport


    if transport == "streamable-http":
        # For HTTP transports, we can use the ASGI app approach to control the event loop
        async def main():
            """Run HTTP transport with file sync support."""

            sync_task = None
            logger.info(f"Sync changes enabled: {app_config.sync_changes}")
            if app_config.sync_changes:
                # Start file sync task in background
                sync_task = asyncio.create_task(initialize_file_sync(app_config))

            # Create ASGI app
            app = mcp_server.http_app(path=path, transport="streamable-http")

            logger.info(f"Starting MCP server with {transport.upper()} transport on http://{host}:{port}{path}")

            # Run with uvicorn
            config = uvicorn.Config(
                app=app,
                host=host,
                port=port,
                log_level="info",
            )
            server = uvicorn.Server(config)

            try:
                await server.serve()
            finally:
                # Cancel sync task on shutdown
                if sync_task:
                    sync_task.cancel()
                    try:
                        await sync_task
                    except asyncio.CancelledError:
                        pass

        # Run the async main function
        asyncio.run(main())
    
    else:
        logger.info("Starting MCP server with stdio transport")
        
        # For stdio, we'll run the file sync in a separate thread since the
        # MCP server will create its own event loop
        import threading
        
        def run_file_sync():
            """Run file sync in a separate thread with its own event loop."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(initialize_file_sync(app_config))
            except Exception as e:
                logger.error(f"File sync error: {e}", err=True)
            finally:
                loop.close()

        logger.info(f"Sync changes enabled: {app_config.sync_changes}")
        if app_config.sync_changes:
            # Start the sync thread
            sync_thread = threading.Thread(target=run_file_sync, daemon=True)
            sync_thread.start()
            logger.info("Started file sync in background")
        
        # Now run the MCP server (blocks)
        mcp_server.run(transport="stdio")