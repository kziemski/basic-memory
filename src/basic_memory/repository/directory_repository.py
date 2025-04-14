"""Repository for directory tree operations."""

import logging
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import text

from basic_memory.repository.repository import Repository

logger = logging.getLogger(__name__)


@dataclass
class FileRow:
    """File node in the directory tree."""

    name: str
    path: str
    title: str
    directory: str
    type: str
    permalink: Optional[str] = None


class DirectoryRepository(Repository):
    """Repository for directory structure operations."""

    def __init__(self, session_maker):
        # Initialize with a dummy model since we're just using the execute_query method
        super().__init__(session_maker, None)  # type: ignore

    async def list_files(self, directory_path: str = "/") -> List[FileRow]:
        """List a directory at a specific path.

        Args:
            directory_path: Base path to start from (empty for root)
        Returns:
            List of DirectoryNode objects representing the directory tree
        """
        logger.debug(f"List files in directory={directory_path}")

        dir_query = text("""
            SELECT id, title, permalink, type, directory, file_path
            FROM search_index
            WHERE directory is not null 
            AND directory like :directory_path 
            ORDER BY directory
        """)
        dir_results = await self.execute_query(
            dir_query, params={"directory_path": f"{directory_path}%"}
        )

        file_rows = [
            FileRow(
                name=r.file_path.split("/")[-1],
                path=r.file_path,
                title=r.title,
                directory=r.directory,
                type=r.type,
                permalink=r.permalink,
            )
            for r in dir_results
        ]
        return file_rows
