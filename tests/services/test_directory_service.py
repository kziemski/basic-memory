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
    result = await directory_service.directory_tree()
    assert isinstance(result, DirectoryTree)
    assert len(result.items) == 0


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

    tree = await directory_service.directory_tree()
    assert isinstance(tree, DirectoryTree)
    assert len(tree.items) == 6  # including root

    test_dir = tree.items.get("test")
    assert test_dir is not None
    assert test_dir.index == "test"
    assert len(test_dir.children) == 5


@pytest.mark.asyncio
async def test_directory_tree_invalid_path(directory_service: DirectoryService, test_graph):
    tree = await directory_service.directory_tree("/invalid")
    assert isinstance(tree, DirectoryTree)
    assert len(tree.items) == 0


@pytest.mark.asyncio
async def test_directory_tree_root(
    entity_service: EntityService,
    directory_service: DirectoryService,
    entity_repository: EntityRepository,
    search_service: SearchService,
):
    # /
    # ├── another
    # │   ├── another_test.md
    # │   └── sub
    # │       └── another_test_sub.md
    # ├── root.md
    # ├── test
    #     ├── sub
    #     │   └── test_sub.md
    #     └── test.md
     
    # /root.md 
    await entity_service.create_entity(
        EntitySchema(
            title="root",
            folder="",
            content="root",
        )
    )

    # /test/test.md
    await entity_service.create_entity(
        EntitySchema(
            title="test",
            folder="test",
            content="test/test",
        )
    )

    # /test/sub/test_sub.md
    await entity_service.create_entity(
        EntitySchema(
            title="test_sub",
            folder="test/sub",
            content="test sub",
        )
    )

    # /another/another_test.md
    await entity_service.create_entity(
        EntitySchema(
            title="another_test",
            folder="another",
            content="another test",
        )
    )

    # /another/sub/another_test_sub.md
    await entity_service.create_entity(
        EntitySchema(
            title="another_test_sub",
            folder="another/sub",
            content="another test sub",
        )
    )

    entities = await entity_repository.find_all()

    # Index everything for search
    for entity in entities:
        await search_service.index_entity(entity)

    tree = await directory_service.directory_tree()
    assert isinstance(tree, DirectoryTree)
    assert len(tree.items) == 10  # including root

    tree_root = tree.items.get("")
    assert tree_root is not None
    assert tree_root.index == ""
    assert len(tree_root.children) == 3
    root_children = [child.index for child in tree_root.children]
    assert "/root.md" in root_children
    assert "/another" in root_children
    assert "/test" in root_children
    
    assert tree.items.get("/root.md")