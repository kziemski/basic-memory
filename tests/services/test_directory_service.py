"""Tests for directory service."""

import pytest

import pytest_asyncio
from basic_memory.repository.directory_repository import DirectoryRepository
from basic_memory.services.directory_service import DirectoryService


@pytest_asyncio.fixture
async def directory_repository(session_maker) -> DirectoryRepository:
    """Create a DirectoryRepository instance."""
    return DirectoryRepository(session_maker)


@pytest_asyncio.fixture
async def directory_service(directory_repository, test_config) -> DirectoryService:
    """Create directory service for testing."""
    return DirectoryService(
        repository=directory_repository,
        base_path=test_config.home,
    )


@pytest.mark.asyncio
async def test_get_directory_tree_empty(directory_service):
    """Test getting empty directory tree."""
    # When no entities exist, tree should be empty
    result = await directory_service.get_directory_tree("", 1, True)
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_directory_tree_with_entities(directory_service, test_graph):
    """Test getting directory tree with multiple entities."""
    # Test graph fixture creates several entities in the "test" folder
    result = await directory_service.get_directory_tree("", 1, True)
    
    # First, check we got some results
    assert len(result) > 0
    
    # Verify we have at least one directory node
    directory_nodes = [node for node in result if node.type == "directory"]
    assert len(directory_nodes) > 0
    assert any(node.name == "test" for node in directory_nodes)
    
    # Check directory node properties
    for directory in directory_nodes:
        assert directory.name is not None
        assert directory.path is not None
        assert directory.type == "directory"
        assert directory.has_children is True
        
    # Check if we have file nodes
    file_nodes = [node for node in result if node.type == "file"]
    if file_nodes:
        # Verify file node properties
        for file in file_nodes:
            assert file.name is not None
            assert file.path is not None
            assert file.type == "file"
            assert file.has_children is False
            # Files at root level should have permalink and entity_id
            assert file.permalink is not None
            assert file.entity_id is not None


@pytest.mark.asyncio
async def test_get_directory_tree_with_path(directory_service, test_graph):
    """Test getting directory tree with specific path."""
    # First get the root level
    root_result = await directory_service.get_directory_tree("", 1, True)
    
    # Find test folder
    test_folder = next((node for node in root_result if node.type == "directory" and node.name == "test"), None)
    assert test_folder is not None
    
    # Now get the contents of the test folder
    test_contents = await directory_service.get_directory_tree(test_folder.path, 1, True)
    
    # Verify we got the entities in the test folder
    assert len(test_contents) > 0
    
    # All items should be under the test folder
    for node in test_contents:
        if node.type == "file":
            assert node.path.startswith(test_folder.path)



@pytest.mark.asyncio
async def test_get_directory_tree_files_only(directory_service, test_graph):
    """Test getting only files in directory tree."""
    # Get directory tree with files
    result_with_files = await directory_service.get_directory_tree("", 1, True)
    assert len(result_with_files) > 0
    
    # Get directory tree with no files
    result_no_files = await directory_service.get_directory_tree("", 1, False)
    
    # There should be fewer results when excluding files
    if len(result_with_files) > len(result_no_files):
        # Some files were excluded
        assert all(node.type == "directory" for node in result_no_files)
    
    # Count files and directories in original result
    file_count = len([node for node in result_with_files if node.type == "file"])
    dir_count = len([node for node in result_with_files if node.type == "directory"])
    
    # No-files result should have only directories
    assert len(result_no_files) == dir_count


@pytest.mark.asyncio
async def test_get_directory_tree_invalid_path(directory_service):
    """Test getting directory tree with invalid path."""
    # Using a path that doesn't exist should return empty results, not error
    result = await directory_service.get_directory_tree("nonexistent_path", 1, True)
    assert isinstance(result, list)
    assert len(result) == 0