"""Main CLI entry point for basic-memory."""  # pragma: no cover

from basic_memory.cli.app import app  # pragma: no cover

# Register commands
from basic_memory.cli.commands import (  # noqa: F401  # pragma: no cover
    auth,
    db,
    import_chatgpt,
    import_claude_conversations,
    import_claude_projects,
    import_memory_json,
    mcp,
    project,
    status,
    sync,
    tool,
)
from basic_memory.config import app_config
from basic_memory.services.initialization import ensure_initialization

if __name__ == "__main__":  # pragma: no cover
    # Run initialization if we are starting as main
    # if running via a typer command, initialization is already run in cli/app.py
    ensure_initialization(app_config)

    # start the app
    app()