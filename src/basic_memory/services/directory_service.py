"""Directory service for managing file directories and tree structure."""

import logging
import os
from pathlib import Path
from typing import List

from basic_memory.repository import EntityRepository
from basic_memory.schemas.directory import DirectoryNode

logger = logging.getLogger(__name__)


class DirectoryService:
    """Service for working with directory trees."""

    def __init__(self, entity_repository: EntityRepository):
        """Initialize the directory service.

        Args:
            repository: Directory repository for data access.
            base_path: Base path for the project.
        """
        self.entity_repository = entity_repository

    async def get_directory_tree(self) -> List[DirectoryNode]:
        """Build a clean directory tree from indexed files."""

        # Get all files from DB (flat list)
        entity_rows = await self.entity_repository.find_all()

        # Create a clean dictionary of directories
        directories = {"/": {"name": "Root", "path": "/", "children": []}}

        # Process files to build tree structure
        for file in entity_rows:
            path = file.file_path
            if not path:
                continue

            # Get all directory parts
            parts = [p for p in path.split("/") if p]
            current_path = "/"

            # Create directory entries for each part of the path
            for i, part in enumerate(parts[:-1]):  # Skip the file name
                parent_path = current_path
                current_path = (
                    f"{current_path}{part}" if current_path == "/" else f"{current_path}/{part}"
                )

                if current_path not in directories:
                    directories[current_path] = {
                        "name": part,
                        "path": current_path,
                        "parent_path": parent_path,
                        "children": [],
                    }
                    directories[parent_path]["children"].append(current_path)

            # Add file to its parent directory
            if parts:
                parent_dir = "/".join(parts[:-1])
                parent_dir = f"/{parent_dir}" if parent_dir else "/"
                if parent_dir in directories:
                    directories[parent_dir]["children"].append(path)

        # Convert to DirectoryNode objects
        result = []
        for path, dir_info in directories.items():
            result.append(
                DirectoryNode(
                    name=dir_info["name"],
                    path=path,
                    type="directory",
                    has_children=bool(dir_info["children"]),
                    parent_path=dir_info.get("parent_path", ""),
                    title=dir_info["name"],
                )
            )

        # Add files
        for file in entity_rows:
            if file.file_path:
                parent_dir = os.path.dirname(file.file_path)
                parent_dir = "/" if parent_dir == "" else f"/{parent_dir}"
                result.append(
                    DirectoryNode(
                        name=os.path.basename(file.file_path),
                        path=file.file_path,
                        type="file",
                        has_children=False,
                        parent_path=parent_dir,
                        title=file.title,
                        permalink=file.permalink,
                        entity_id=file.id,
                        entity_type=file.entity_type,
                        content_type=file.content_type,
                        updated_at=file.updated_at,
                    )
                )

        return result