"""MCP server command."""

import basic_memory
from basic_memory.cli.app import app

# Import mcp instance
from basic_memory.mcp.server import mcp as mcp_server  # pragma: no cover

# Import mcp tools to register them
import basic_memory.mcp.tools  # noqa: F401  # pragma: no cover


@app.command()
def mcp():  # pragma: no cover
    """Run the MCP server"""
    from basic_memory.config import app_config
    import asyncio
    from basic_memory.services.initialization import initialize_database

    # run the database migrations synchronously
    asyncio.run(initialize_database(app_config))

    # Start the MCP server
    mcp_server.run()
