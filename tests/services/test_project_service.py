"""Tests for ProjectService."""

import os

import pytest

from basic_memory.schemas import (
    ProjectInfoResponse,
    ProjectStatistics,
    ActivityMetrics,
    SystemStatus,
)
from basic_memory.services.project_service import ProjectService


def test_projects_property(project_service: ProjectService):
    """Test the projects property."""
    # Get the projects
    projects = project_service.projects

    # Assert that it returns a dictionary
    assert isinstance(projects, dict)
    # The test config should have at least one project
    assert len(projects) > 0


def test_default_project_property(project_service: ProjectService):
    """Test the default_project property."""
    # Get the default project
    default_project = project_service.default_project

    # Assert it's a string and has a value
    assert isinstance(default_project, str)
    assert default_project


def test_current_project_property(project_service: ProjectService):
    """Test the current_project property."""
    # Save original environment
    original_env = os.environ.get("BASIC_MEMORY_PROJECT")

    try:
        # Test with environment variable not set
        if "BASIC_MEMORY_PROJECT" in os.environ:
            del os.environ["BASIC_MEMORY_PROJECT"]

        # Should return default_project when env var not set
        assert project_service.current_project == project_service.default_project

        # Now set the environment variable
        os.environ["BASIC_MEMORY_PROJECT"] = "test-project"

        # Should return env var value
        assert project_service.current_project == "test-project"
    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["BASIC_MEMORY_PROJECT"] = original_env
        elif "BASIC_MEMORY_PROJECT" in os.environ:
            del os.environ["BASIC_MEMORY_PROJECT"]

    """Test the methods of ProjectService."""


def test_project_operations(project_service: ProjectService, tmp_path):
    """Test adding, switching, and removing a project."""
    # Generate a unique project name for testing
    test_project_name = f"test-project-{os.urandom(4).hex()}"
    test_project_path = str(tmp_path / "test-project")

    # Make sure the test directory exists
    os.makedirs(test_project_path, exist_ok=True)

    try:
        # Test adding a project
        project_service.add_project(test_project_name, test_project_path)

        # Verify it was added
        assert test_project_name in project_service.projects
        assert project_service.projects[test_project_name] == test_project_path

        # Test switching to the project
        original_env = os.environ.get("BASIC_MEMORY_PROJECT")
        try:
            project_service.switch_project(test_project_name)
            assert os.environ.get("BASIC_MEMORY_PROJECT") == test_project_name
        finally:
            # Restore original environment
            if original_env is not None:
                os.environ["BASIC_MEMORY_PROJECT"] = original_env
            elif "BASIC_MEMORY_PROJECT" in os.environ:
                del os.environ["BASIC_MEMORY_PROJECT"]

        # Test setting as default
        original_default = project_service.default_project
        project_service.set_default_project(test_project_name)
        assert project_service.default_project == test_project_name

        # Restore original default
        if original_default:
            project_service.set_default_project(original_default)

        # Test error when switching to non-existent project
        with pytest.raises(ValueError):
            project_service.switch_project("non-existent-project")

        # Test removing the project
        project_service.remove_project(test_project_name)
        assert test_project_name not in project_service.projects

    except Exception as e:
        # Clean up in case of error
        if test_project_name in project_service.projects:
            try:
                project_service.remove_project(test_project_name)
            except Exception:
                pass
        raise e


@pytest.mark.asyncio
async def test_get_system_status(project_service: ProjectService):
    """Test getting system status."""
    # Get the system status
    status = project_service.get_system_status()

    # Assert it returns a valid SystemStatus object
    assert isinstance(status, SystemStatus)
    assert status.version
    assert status.database_path
    assert status.database_size


@pytest.mark.asyncio
async def test_get_statistics(project_service: ProjectService, test_graph):
    """Test getting statistics."""
    # Get statistics
    statistics = await project_service.get_statistics()

    # Assert it returns a valid ProjectStatistics object
    assert isinstance(statistics, ProjectStatistics)
    assert statistics.total_entities > 0
    assert "test" in statistics.entity_types

    # Test with no repository
    temp_service = ProjectService()  # No repository provided
    with pytest.raises(ValueError, match="Repository is required for get_statistics"):
        await temp_service.get_statistics()


@pytest.mark.asyncio
async def test_get_activity_metrics(project_service: ProjectService, test_graph):
    """Test getting activity metrics."""
    # Get activity metrics
    metrics = await project_service.get_activity_metrics()

    # Assert it returns a valid ActivityMetrics object
    assert isinstance(metrics, ActivityMetrics)
    assert len(metrics.recently_created) > 0
    assert len(metrics.recently_updated) > 0

    # Test with no repository
    temp_service = ProjectService()  # No repository provided
    with pytest.raises(ValueError, match="Repository is required for get_activity_metrics"):
        await temp_service.get_activity_metrics()


@pytest.mark.asyncio
async def test_get_project_info(project_service: ProjectService, test_graph):
    """Test getting full project info."""
    # Get project info
    info = await project_service.get_project_info()

    # Assert it returns a valid ProjectInfoResponse object
    assert isinstance(info, ProjectInfoResponse)
    assert info.project_name
    assert info.project_path
    assert info.default_project
    assert isinstance(info.available_projects, dict)
    assert isinstance(info.statistics, ProjectStatistics)
    assert isinstance(info.activity, ActivityMetrics)
    assert isinstance(info.system, SystemStatus)

    # Test with no repository
    temp_service = ProjectService()  # No repository provided
    with pytest.raises(ValueError, match="Repository is required for get_project_info"):
        await temp_service.get_project_info()
