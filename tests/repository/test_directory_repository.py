"""Tests for directory service."""

import pytest

from basic_memory.repository.directory_repository import DirectoryRepository


@pytest.mark.asyncio
async def test_list_files_empty(directory_repository: DirectoryRepository):
    result = await directory_repository.list_files("")
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_list_files(directory_repository: DirectoryRepository, test_graph):

    # test_graph files:
    # /
    # ├── test
    # │   ├── Connected Entity 1.md
    # │   ├── Connected Entity 2.md
    # │   ├── Deep Entity.md
    # │   ├── Deeper Entity.md
    # │   └── Root.md
    
    result = await directory_repository.list_files("/test")
    assert len(result) == 5

    result_root = await directory_repository.list_files("/")
    assert len(result_root) == 5

    result_default = await directory_repository.list_files()
    assert len(result_default) == 5


@pytest.mark.asyncio
async def test_get_directory_tree_invalid_path(directory_repository: DirectoryRepository, test_graph):
    result = await directory_repository.list_files("/invalid")
    assert len(result) == 0
