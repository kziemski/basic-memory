"""Tests for the initialization service."""

from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from basic_memory.services.initialization import (
    ensure_initialization,
    initialize_app,
    initialize_database,
    reconcile_projects_with_config,
    migrate_legacy_projects,
    migrate_legacy_project_data,
)


@pytest.mark.asyncio
@patch("basic_memory.services.initialization.db.run_migrations")
async def test_initialize_database(mock_run_migrations, test_config):
    """Test initializing the database."""
    await initialize_database(test_config)
    mock_run_migrations.assert_called_once_with(test_config)


@pytest.mark.asyncio
@patch("basic_memory.services.initialization.db.run_migrations")
async def test_initialize_database_error(mock_run_migrations, test_config):
    """Test handling errors during database initialization."""
    mock_run_migrations.side_effect = Exception("Test error")
    await initialize_database(test_config)
    mock_run_migrations.assert_called_once_with(test_config)


@pytest.mark.asyncio
@patch("basic_memory.services.initialization.reconcile_projects_with_config")
@patch("basic_memory.services.initialization.migrate_legacy_projects")
@patch("basic_memory.services.initialization.initialize_database")
@patch("basic_memory.services.initialization.initialize_file_sync")
async def test_initialize_app(
    mock_initialize_file_sync, 
    mock_initialize_database, 
    mock_migrate_legacy_projects,
    mock_reconcile_projects,
    app_config
):
    """Test app initialization."""
    mock_initialize_file_sync.return_value = "task"

    result = await initialize_app(app_config)

    mock_initialize_database.assert_called_once_with(app_config)
    mock_reconcile_projects.assert_called_once_with(app_config)
    mock_migrate_legacy_projects.assert_called_once_with(app_config)
    mock_initialize_file_sync.assert_called_once_with(app_config)
    assert result == "task"


@pytest.mark.asyncio
@patch("basic_memory.services.initialization.initialize_database")
@patch("basic_memory.services.initialization.reconcile_projects_with_config")
@patch("basic_memory.services.initialization.migrate_legacy_projects")
async def test_initialize_app_sync_disabled(
    mock_migrate_legacy_projects,
    mock_reconcile_projects,
    mock_initialize_database, 
    app_config
):
    """Test app initialization with sync disabled."""
    app_config.sync_changes = False
    
    result = await initialize_app(app_config)

    mock_initialize_database.assert_called_once_with(app_config)
    mock_reconcile_projects.assert_called_once_with(app_config)
    mock_migrate_legacy_projects.assert_called_once_with(app_config)
    assert result is None


@patch("basic_memory.services.initialization.asyncio.run")
def test_ensure_initialization(mock_run, test_config):
    """Test synchronous initialization wrapper."""
    ensure_initialization(test_config)
    mock_run.assert_called_once()


@pytest.mark.asyncio
@patch("basic_memory.services.initialization.db.get_or_create_db")
async def test_reconcile_projects_with_config(mock_get_db, app_config):
    """Test reconciling projects from config with database."""
    # Setup mocks
    mock_session_maker = AsyncMock()
    mock_get_db.return_value = (None, mock_session_maker)
    
    mock_repository = AsyncMock()
    mock_project = MagicMock()
    mock_project.name = "test_project"
    
    # Mock the repository and its methods
    with patch("basic_memory.services.initialization.ProjectRepository") as mock_repo_class:
        mock_repo_class.return_value = mock_repository
        mock_repository.find_all.return_value = [mock_project]
        mock_repository.get_by_name.return_value = mock_project
        
        # Set up app_config projects
        app_config.projects = [("test_project", "/path/to/project"), ("new_project", "/path/to/new")]
        app_config.default_project = "test_project"
        
        # Run the function
        await reconcile_projects_with_config(app_config)
        
        # Assertions
        mock_get_db.assert_called_once()
        mock_repository.find_all.assert_called_once()
        assert mock_repository.create.call_count == 1
        mock_repository.set_as_default.assert_called_once_with(project_id=mock_project.id)


@pytest.mark.asyncio
@patch("basic_memory.services.initialization.db.get_or_create_db")
async def test_reconcile_projects_with_missing_default(mock_get_db, app_config):
    """Test reconciling projects with missing default project."""
    # Setup mocks
    mock_session_maker = AsyncMock()
    mock_get_db.return_value = (None, mock_session_maker)
    
    mock_repository = AsyncMock()
    
    # Mock the repository and its methods
    with patch("basic_memory.services.initialization.ProjectRepository") as mock_repo_class:
        mock_repo_class.return_value = mock_repository
        mock_repository.find_all.return_value = []
        mock_repository.get_by_name.return_value = None
        
        # Set up app_config projects
        app_config.projects = [("test_project", "/path/to/project")]
        app_config.default_project = "missing_project"
        
        # Run the function and assert it raises an error
        with pytest.raises(ValueError, match="Default project missing_project not found in database"):
            await reconcile_projects_with_config(app_config)


@pytest.mark.asyncio
@patch("basic_memory.services.initialization.db.get_or_create_db")
async def test_migrate_legacy_projects_no_legacy_dirs(mock_get_db, app_config):
    """Test migration when no legacy dirs exist."""
    # Setup mocks
    mock_session_maker = AsyncMock()
    mock_get_db.return_value = (None, mock_session_maker)
    
    mock_repository = AsyncMock()
    
    with patch("basic_memory.services.initialization.Path") as mock_path, \
         patch("basic_memory.services.initialization.ProjectRepository") as mock_repo_class, \
         patch("basic_memory.services.initialization.migrate_legacy_project_data") as mock_migrate:
        
        # Create a mock for the Path instance
        mock_legacy_dir = MagicMock()
        mock_legacy_dir.exists.return_value = False
        mock_path.return_value.__truediv__.return_value = mock_legacy_dir
        
        mock_repo_class.return_value = mock_repository
        
        # Set up app_config projects
        app_config.projects = [("test_project", "/path/to/project")]
        
        # Run the function
        await migrate_legacy_projects(app_config)
        
        # Assertions - should not call get_by_name or migrate_legacy_project_data
        mock_repository.get_by_name.assert_not_called()
        mock_migrate.assert_not_called()


@pytest.mark.asyncio
@patch("basic_memory.services.initialization.migrate_legacy_project_data")
@patch("basic_memory.services.initialization.db.get_or_create_db")
async def test_migrate_legacy_projects_with_legacy_dirs(
    mock_get_db, mock_migrate_legacy, app_config, tmp_path
):
    """Test migration with legacy dirs."""
    # Setup mocks
    mock_session_maker = AsyncMock()
    mock_get_db.return_value = (None, mock_session_maker)
    
    mock_repository = AsyncMock()
    mock_project = MagicMock()
    mock_project.name = "test_project"
    mock_project.id = 1  # Add numeric ID
    
    # Create a temporary legacy dir
    legacy_dir = tmp_path / ".basic-memory"
    legacy_dir.mkdir(exist_ok=True)
    
    # Mock the repository
    with patch("basic_memory.services.initialization.ProjectRepository") as mock_repo_class:
        mock_repo_class.return_value = mock_repository
        mock_repository.get_by_name.return_value = mock_project
        
        # Set up app_config projects
        app_config.projects = [("test_project", str(tmp_path))]
        
        # Run the function
        with patch("basic_memory.services.initialization.Path", lambda x: Path(x)):
            await migrate_legacy_projects(app_config)
        
        # Assertions
        mock_repository.get_by_name.assert_called_once_with("test_project")
        mock_migrate_legacy.assert_called_once_with(mock_project, legacy_dir)


@pytest.mark.asyncio
@patch("basic_memory.services.initialization.shutil.rmtree")
async def test_migrate_legacy_project_data_success(mock_rmtree, tmp_path):
    """Test successful migration of legacy project data."""
    # Setup mocks
    mock_project = MagicMock()
    mock_project.name = "test_project"
    mock_project.path = str(tmp_path)
    mock_project.id = 1  # Add numeric ID
    
    mock_sync_service = AsyncMock()
    mock_sync_service.sync = AsyncMock()
    
    # Create a legacy dir
    legacy_dir = tmp_path / ".basic-memory"
    
    # Run the function
    with patch("basic_memory.cli.commands.sync.get_sync_service", 
               AsyncMock(return_value=mock_sync_service)):
        result = await migrate_legacy_project_data(mock_project, legacy_dir)
    
    # Assertions
    mock_sync_service.sync.assert_called_once_with(Path(mock_project.path))
    mock_rmtree.assert_called_once_with(legacy_dir)
    assert result is True


@pytest.mark.asyncio
@patch("basic_memory.services.initialization.shutil.rmtree")
async def test_migrate_legacy_project_data_rmtree_error(mock_rmtree, tmp_path):
    """Test migration of legacy project data with rmtree error."""
    # Setup mocks
    mock_project = MagicMock()
    mock_project.name = "test_project"
    mock_project.path = str(tmp_path)
    mock_project.id = 1  # Add numeric ID
    
    mock_sync_service = AsyncMock()
    mock_sync_service.sync = AsyncMock()
    
    # Make rmtree raise an exception
    mock_rmtree.side_effect = Exception("Test error")
    
    # Create a legacy dir
    legacy_dir = tmp_path / ".basic-memory"
    
    # Run the function
    with patch("basic_memory.cli.commands.sync.get_sync_service", 
               AsyncMock(return_value=mock_sync_service)):
        result = await migrate_legacy_project_data(mock_project, legacy_dir)
    
    # Assertions
    mock_sync_service.sync.assert_called_once_with(Path(mock_project.path))
    mock_rmtree.assert_called_once_with(legacy_dir)
    assert result is False
