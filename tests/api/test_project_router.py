"""Tests for the project router API endpoints."""

import json
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_get_project_info_endpoint(test_graph, client, test_config):
    """Test the project-info endpoint returns correctly structured data."""
    # Set up some test data in the database

    # Call the endpoint
    response = await client.get("/project/info")

    # Verify response
    assert response.status_code == 200
    data = response.json()

    # Check top-level keys
    assert "project_name" in data
    assert "project_path" in data
    assert "available_projects" in data
    assert "default_project" in data
    assert "statistics" in data
    assert "activity" in data
    assert "system" in data

    # Check statistics
    stats = data["statistics"]
    assert "total_entities" in stats
    assert stats["total_entities"] >= 0
    assert "total_observations" in stats
    assert stats["total_observations"] >= 0
    assert "total_relations" in stats
    assert stats["total_relations"] >= 0

    # Check activity
    activity = data["activity"]
    assert "recently_created" in activity
    assert "recently_updated" in activity
    assert "monthly_growth" in activity

    # Check system
    system = data["system"]
    assert "version" in system
    assert "database_path" in system
    assert "database_size" in system
    assert "timestamp" in system


@pytest.mark.asyncio
async def test_get_project_info_content(test_graph, client, test_config):
    """Test that project-info contains actual data from the test database."""
    # Call the endpoint
    response = await client.get("/project/info")

    # Verify response
    assert response.status_code == 200
    data = response.json()

    # Check that test_graph content is reflected in statistics
    stats = data["statistics"]

    # Our test graph should have at least a few entities
    assert stats["total_entities"] > 0

    # It should also have some observations
    assert stats["total_observations"] > 0

    # And relations
    assert stats["total_relations"] > 0

    # Check that entity types include 'test'
    assert "test" in stats["entity_types"] or "entity" in stats["entity_types"]


@pytest.mark.asyncio
async def test_get_project_info_watch_status(test_graph, client, test_config):
    """Test that project-info correctly handles watch status."""
    # Create a mock watch status file
    mock_watch_status = {
        "running": True,
        "start_time": "2025-03-05T18:00:42.752435",
        "pid": 7321,
        "error_count": 0,
        "last_error": None,
        "last_scan": "2025-03-05T19:59:02.444416",
        "synced_files": 6,
        "recent_events": [],
    }

    # Mock the Path.exists and Path.read_text methods
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=json.dumps(mock_watch_status)),
    ):
        # Call the endpoint
        response = await client.get("/project/info")

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Check that watch status is included
        assert data["system"]["watch_status"] is not None
        assert data["system"]["watch_status"]["running"] is True
        assert data["system"]["watch_status"]["pid"] == 7321
        assert data["system"]["watch_status"]["synced_files"] == 6


@pytest.mark.asyncio
async def test_list_projects_endpoint(test_graph, client, test_config):
    """Test the list projects endpoint returns correctly structured data."""
    # Call the endpoint
    response = await client.get("/project/projects")

    # Verify response
    assert response.status_code == 200
    data = response.json()

    # Check that the response contains expected fields
    assert "projects" in data
    assert "default_project" in data
    assert "current_project" in data

    # Check that projects is a list
    assert isinstance(data["projects"], list)

    # There should be at least one project (the test project)
    assert len(data["projects"]) > 0

    # Verify project item structure
    if data["projects"]:
        project = data["projects"][0]
        assert "name" in project
        assert "path" in project
        assert "is_default" in project
        assert "is_current" in project

        # Current project should be marked
        current_project = next((p for p in data["projects"] if p["is_current"]), None)
        assert current_project is not None
        assert current_project["name"] == data["current_project"]

        # Default project should be marked
        default_project = next((p for p in data["projects"] if p["is_default"]), None)
        assert default_project is not None
        assert default_project["name"] == data["default_project"]


@pytest.mark.asyncio
async def test_switch_project_endpoint(test_graph, client, test_config):
    """Test the switch project endpoint."""
    # First get the list of projects
    projects_response = await client.get("/project/projects")
    projects_data = projects_response.json()

    # Get a project that is not the current one
    current_project = projects_data["current_project"]

    # If there's only one project, we can't test switching
    if len(projects_data["projects"]) <= 1:
        pytest.skip("Need at least two projects to test switching")

    # Find another project
    other_project = next(
        (p["name"] for p in projects_data["projects"] if p["name"] != current_project), None
    )

    if not other_project:
        pytest.skip("Could not find a different project to switch to")

    # Now try to switch to the other project
    switch_response = await client.post(
        "/project/switch", json={"name": other_project, "set_default": False}
    )

    # Verify response
    assert switch_response.status_code == 200
    switch_data = switch_response.json()

    # Check the response structure
    assert "message" in switch_data
    assert "status" in switch_data
    assert "default" in switch_data

    # Verify the switch was successful
    assert switch_data["status"] == "success"
    assert other_project in switch_data["message"]
    assert switch_data["default"] is False

    # Verify that the current project was actually changed
    updated_projects_response = await client.get("/project/projects")
    updated_projects_data = updated_projects_response.json()

    assert updated_projects_data["current_project"] == other_project

    # Now switch back to the original project
    await client.post("/project/switch", json={"name": current_project, "set_default": False})


@pytest.mark.asyncio
async def test_switch_project_with_default_endpoint(test_graph, client, test_config):
    """Test switching projects with the set_default flag."""
    # First get the list of projects
    projects_response = await client.get("/project/projects")
    projects_data = projects_response.json()

    # Get a project that is not the current one
    _ = projects_data["current_project"]
    default_project = projects_data["default_project"]

    # If there's only one project, we can't test switching
    if len(projects_data["projects"]) <= 1:
        pytest.skip("Need at least two projects to test switching")

    # Find another project that is not the default
    other_project = next(
        (p["name"] for p in projects_data["projects"] if p["name"] != default_project), None
    )

    if not other_project:
        pytest.skip("Could not find a non-default project to switch to")

    # Now try to switch to the other project and set it as default
    switch_response = await client.post(
        "/project/switch", json={"name": other_project, "set_default": True}
    )

    # Verify response
    assert switch_response.status_code == 200
    switch_data = switch_response.json()

    # Verify the switch was successful and default was set
    assert switch_data["status"] == "success"
    assert other_project in switch_data["message"]
    assert switch_data["default"] is True

    # Verify that the current and default project were both changed
    updated_projects_response = await client.get("/project/projects")
    updated_projects_data = updated_projects_response.json()

    assert updated_projects_data["current_project"] == other_project
    assert updated_projects_data["default_project"] == other_project

    # Now switch back to the original default
    await client.post("/project/switch", json={"name": default_project, "set_default": True})


@pytest.mark.asyncio
async def test_switch_project_invalid_project(test_graph, client, test_config):
    """Test switching to an invalid project."""
    # Try to switch to a project that doesn't exist
    switch_response = await client.post(
        "/project/switch", json={"name": "nonexistent_project", "set_default": False}
    )

    # Should get a 404 error
    assert switch_response.status_code == 404
