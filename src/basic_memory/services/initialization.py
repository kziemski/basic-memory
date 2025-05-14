"""Shared initialization service for Basic Memory.

This module provides shared initialization functions used by both CLI and API
to ensure consistent application startup across all entry points.
"""

import asyncio
from pathlib import Path

from loguru import logger

from basic_memory import db
from basic_memory.config import ProjectConfig, config_manager, BasicMemoryConfig
from basic_memory.models import Project
from basic_memory.repository import ProjectRepository


async def initialize_database(app_config: BasicMemoryConfig) -> None:
    """Run database migrations to ensure schema is up to date.

    Args:
        app_config: The Basic Memory project configuration
    """
    try:
        logger.info("Running database migrations...")
        await db.run_migrations(app_config)
        logger.info("Migrations completed successfully")
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        # Allow application to continue - it might still work
        # depending on what the error was, and will fail with a
        # more specific error if the database is actually unusable


async def initialize_file_sync(
    app_config: BasicMemoryConfig,
):
    """Initialize file synchronization services.

    Args:
        app_config: The Basic Memory project configuration

    Returns:
        Tuple of (sync_service, watch_service, watch_task) if sync is enabled,
        or (None, None, None) if sync is disabled
    """

    # delay import
    from basic_memory.sync import WatchService

    # Load app configuration
    _, session_maker = await db.get_or_create_db(
        db_path=app_config.database_path, db_type=db.DatabaseType.FILESYSTEM
    )
    project_repository = ProjectRepository(session_maker)

    # Initialize watch service
    watch_service = WatchService(
        app_config=app_config,
        project_repository=project_repository,
        quiet=True,
    )

    # background task for running sync
    async def run_background_sync(project: Project):  # pragma: no cover
        # Run initial full sync

        # avoid circular imports
        from basic_memory.cli.commands.sync import get_sync_service

        sync_service = await get_sync_service(project)
        sync_dir = Path(project.path)

        await sync_service.sync(sync_dir)
        logger.info("Sync completed successfully")

        # Start background sync task
        logger.info(f"Starting watch service to sync file changes in dir: {app_config.home}")

        # Start watching for changes
        await watch_service.run()

    sync_tasks = [
        run_background_sync(project) for project in await project_repository.get_active_projects()
    ]

    watch_tasks = asyncio.gather(*sync_tasks)
    logger.info("Watch service started")
    return watch_tasks


async def initialize_app(
    app_config: BasicMemoryConfig,
):
    """Initialize the Basic Memory application.

    This function handles all initialization steps needed for both API and short lived CLI commands.
    For long running commands like mcp, a
    - Running database migrations
    - Setting up file synchronization

    Args:
        app_config: The Basic Memory project configuration
    """
    # Initialize database first
    await initialize_database(app_config)

    basic_memory_config = config_manager.load_config()
    logger.info(f"Sync changes enabled: {basic_memory_config.sync_changes}")
    logger.info(
        f"Update permalinks on move enabled: {basic_memory_config.update_permalinks_on_move}"
    )
    if not basic_memory_config.sync_changes:  # pragma: no cover
        logger.info("Sync changes disabled. Skipping watch service.")
        return

    # Initialize file sync services
    return await initialize_file_sync(app_config)


def ensure_initialization(app_config: BasicMemoryConfig) -> None:
    """Ensure initialization runs in a synchronous context.

    This is a wrapper for the async initialize_app function that can be
    called from synchronous code like CLI entry points.

    Args:
        app_config: The Basic Memory project configuration
    """
    try:
        asyncio.run(initialize_app(app_config))
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        # Continue execution even if initialization fails
        # The command might still work, or will fail with a
        # more specific error message


def ensure_initialize_database(app_config: BasicMemoryConfig) -> None:
    """Ensure initialization runs in a synchronous context.

    This is a wrapper for the async initialize_database function that can be
    called from synchronous code like CLI entry points.

    Args:
        app_config: The Basic Memory project configuration
    """
    try:
        asyncio.run(initialize_database(app_config))
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        # Continue execution even if initialization fails
        # The command might still work, or will fail with a
        # more specific error message