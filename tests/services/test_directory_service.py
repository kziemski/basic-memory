"""Tests for directory service."""

import pytest

from basic_memory.repository import EntityRepository
from basic_memory.schemas import DirectoryTree, Entity as EntitySchema
from basic_memory.services.directory_service import DirectoryService
from basic_memory.services.entity_service import EntityService
from basic_memory.services.search_service import SearchService


@pytest.mark.asyncio
async def test_directory_tree_empty(directory_service: DirectoryService):
    """Test getting empty directory tree."""
    # When no entities exist, tree should be empty
    result = await directory_service.get_directory_tree()
    assert len(result) == 1

    root = result[0]
    assert root.name == "Root"
    assert root.path == "/"
    assert root.has_children is False


@pytest.mark.asyncio
async def test_directory_tree(directory_service: DirectoryService, test_graph):
    # test_graph files:
    # /
    # ├── test
    # │   ├── Connected Entity 1.md
    # │   ├── Connected Entity 2.md
    # │   ├── Deep Entity.md
    # │   ├── Deeper Entity.md
    # │   └── Root.md

    result = await directory_service.get_directory_tree()

    assert len(result) == 7 # 5 files, 2 dirs
    node_0 = result[0]
    assert node_0.name == "Root"
    assert node_0.path == "/"
    assert node_0.has_children is True

    node_1 = result[1]
    assert node_1.name == "test"
    assert node_1.path == "/test"
    assert node_1.type == "directory"
    assert node_1.permalink is None
    assert node_1.entity_type is None
    assert node_1.content_type is None
    assert node_1.updated_at is None
    assert node_1.parent_path == "/"

    # just assert one file
    node_2 = result[2]
    assert node_2.name == "Deeper Entity.md"
    assert node_2.path == "test/Deeper Entity.md"
    assert node_2.type == "file"
    assert node_2.permalink == "test/deeper-entity"
    assert node_2.entity_id is not None
    assert node_2.entity_type == "deeper"
    assert node_2.content_type == "text/markdown"
    assert node_2.updated_at is not None
    assert node_2.parent_path == "/test"
