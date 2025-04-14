"""Directory service for managing file directories and tree structure."""

import logging
from pathlib import Path
from typing import Dict

from basic_memory.repository.directory_repository import DirectoryRepository
from basic_memory.schemas import DirectoryTree, DirectoryItem

logger = logging.getLogger(__name__)


class DirectoryService:
    """Service for working with directory trees."""

    def __init__(self, repository: DirectoryRepository, base_path: Path):
        """Initialize the directory service.

        Args:
            repository: Directory repository for data access.
            base_path: Base path for the project.
        """
        self.repository = repository
        self.base_path = base_path

    async def directory_tree(
        self, directory_path: str = "", include_files: bool = True
    ) -> DirectoryTree:
        """Get directory tree at a specific depth level.

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
        
        tree
        
        const items = {
          root: {
            index: 'root',
            canMove: true,
            isFolder: true,
            children: ['child1', 'child2'],
            data: 'Root item',
            canRename: true,
          },
          child1: {
            index: 'child1',
            canMove: true,
            isFolder: false,
            children: [],
            data: 'Child item 1',
            canRename: true,
          },
          child2: {
            index: 'child2',
            canMove: true,
            isFolder: false,
            children: [],
            data: 'Child item 2',
            canRename: true,
          },
        };

        Args:
            directory_path: Directory path to start from (empty for root)
            include_files: Whether to include files in the tree
        Returns:
            DirectoryTree object representing the hierarchy
            
        """
        file_rows = await self.repository.list_files(directory_path)
        directory_items: Dict[str, DirectoryItem] = {}

        for file_row in file_rows:
            # Use the file path as the index
            index = file_row.path
            directory = file_row.directory
            
            # Get the parent's children list
            parent_path = str(Path(file_row.path).parent)
            if parent_path == ".":
                parent_path = ""

            # Create or update parent's children list
            if parent_path in directory_items:
                directory_items[parent_path].children.append(index)
            else:
                directory_items[parent_path] = DirectoryItem(
                    index=parent_path,
                    canMove=True,
                    isFolder=True,
                    children=[index],
                    data=Path(parent_path).name or "Root",
                    canRename=True,
                )

            # Add the file/directory item
            directory_items[index] = DirectoryItem(
                index=index,
                canMove=True,
                isFolder=False,
                children=[],  
                data=file_row.name,
                canRename=True,
            )

        return DirectoryTree(items=directory_items)
