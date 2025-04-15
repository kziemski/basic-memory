"""Directory service for managing file directories and tree structure."""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from basic_memory.repository.directory_repository import DirectoryRepository, FileRow
from basic_memory.schemas.directory import (
    DirectoryTree, 
    DirectoryItem, 
    DirectoryNode, 
    DirectoryTreeResponse
)

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
        """Get directory tree in the old format.

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
        
    async def list_files(
        self, directory_path: str = "", include_files: bool = True, depth: int = 1
    ) -> List[DirectoryNode]:
        """Get directory contents as a flat list.
        
        This returns a list of DirectoryNode objects representing files and directories
        at the given path, formatted for the API response expected by the client.
        
        Args:
            directory_path: Directory path to start from (empty for root)
            include_files: Whether to include files or just directories
            depth: How deep to traverse the directory tree (default: 1 level)
            
        Returns:
            List of DirectoryNode objects
        """
        # Get file rows directly from repository - our improved repository implementation
        # already handles directory structure correctly
        file_rows = await self.repository.list_files(directory_path)
        
        # Convert to DirectoryNode objects
        result_nodes: List[DirectoryNode] = []
        
        for row in file_rows:
            # Skip files if not including files
            if not include_files and row.type not in ["directory"]:
                continue
                
            # Calculate parent path
            parent_path = os.path.dirname(row.path)
            if parent_path == ".":
                parent_path = ""
                
            # Determine node type - directory or file
            node_type = "directory" if row.type == "directory" else "file"
            
            # Add to result nodes
            result_nodes.append(
                DirectoryNode(
                    name=row.name,
                    path=row.path,
                    type=node_type,
                    has_children=(node_type == "directory"),  # Directories have children
                    title=row.title,
                    permalink=row.permalink,
                    entity_id=row.entity_id,
                    entity_type=row.type if node_type == "file" else None,
                    content_type=row.content_type,
                    updated_at=row.updated_at,
                    parent_path=parent_path
                )
            )
        
        # Sort results: directories first, then alphabetically by name
        result_nodes.sort(
            key=lambda x: (
                0 if x.type == "directory" else 1,  # Directories first
                x.name.lower()  # Then alphabetically
            )
        )
        
        return result_nodes
