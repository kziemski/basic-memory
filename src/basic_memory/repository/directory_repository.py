"""Repository for directory tree operations."""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Dict

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
    entity_id: Optional[int] = None
    content_type: Optional[str] = None
    updated_at: Optional[datetime] = None


class DirectoryRepository(Repository):
    """Repository for directory structure operations."""

    def __init__(self, session_maker):
        # Initialize with a dummy model since we're just using the execute_query method
        super().__init__(session_maker, None)  # type: ignore

    async def list_files(self, directory_path: str = "") -> List[FileRow]:
        """List a directory at a specific path.

        Args:
            directory_path: Base path to start from (empty for root)
        Returns:
            List of DirectoryNode objects representing the directory tree
        """
        logger.debug(f"List files in directory={directory_path}")

        # Normalize path for database query
        normalized_path = directory_path.rstrip('/')
        
        # Prepare search path for LIKE query
        if normalized_path:
            search_path = f"/{normalized_path}/%"
            exact_path = f"/{normalized_path}"
        else:
            # Root path
            search_path = "/%"
            exact_path = "/"
            
        # First query: Find entity files directly in the specified directory
        # This will get files that are exactly at the given directory level
        entity_query = text("""
            SELECT 
                e.id as entity_id, 
                e.title, 
                e.entity_type as type, 
                e.content_type, 
                e.permalink, 
                e.file_path,
                e.updated_at,
                si.directory
            FROM 
                entity e
            LEFT JOIN 
                search_index si ON e.id = si.entity_id
            WHERE 
                si.directory = :exact_path
            ORDER BY 
                e.title
        """)
        
        # Second query: Get unique directories at the current level
        # This finds immediate subdirectories without going deeper
        directory_query = text("""
            SELECT DISTINCT
                substr(directory, 1, instr(substr(directory, length(:exact_path) + 2), '/') + length(:exact_path) + 1) AS subdir
            FROM 
                search_index
            WHERE 
                directory LIKE :search_path 
                AND directory != :exact_path
                AND instr(substr(directory, length(:exact_path) + 2), '/') > 0
            ORDER BY 
                subdir
        """)
        
        # Execute both queries in parallel
        entity_results = await self.execute_query(
            entity_query, 
            params={"exact_path": exact_path}
        )
        
        directory_results = await self.execute_query(
            directory_query, 
            params={
                "exact_path": exact_path,
                "search_path": search_path
            }
        )
        
        # Process entities
        file_rows = []
        seen_paths = set()
        
        # Process direct entities (files) first
        for r in entity_results:
            if not r.file_path:  # Skip entries without a file path
                continue
                
            file_name = Path(r.file_path).name
            file_path = r.file_path
            
            # Add to result if not already seen
            if file_path not in seen_paths:
                seen_paths.add(file_path)
                file_rows.append(
                    FileRow(
                        name=file_name,
                        path=file_path,
                        title=r.title or file_name,
                        directory=r.directory or exact_path,
                        type=r.type,
                        permalink=r.permalink,
                        entity_id=r.entity_id,
                        content_type=r.content_type,
                        updated_at=r.updated_at
                    )
                )
        
        # Process immediate directories
        for r in directory_results:
            subdir = r.subdir
            if not subdir or subdir in seen_paths:
                continue
                
            # Extract directory name from path
            dir_name = Path(subdir).name
            if not dir_name:
                dir_name = subdir.split('/')[-1]
                
            seen_paths.add(subdir)
            
            # Create a synthetic directory entry
            file_rows.append(
                FileRow(
                    name=dir_name,
                    path=subdir,
                    title=dir_name,
                    directory=exact_path,
                    type="directory",
                    permalink=None,
                    entity_id=None,
                    content_type="directory",
                    updated_at=None
                )
            )
        
        # Special case: Root level also needs to scan top-level directories
        if not normalized_path:
            root_dirs_query = text("""
                SELECT DISTINCT
                    substr(directory, 2, instr(substr(directory, 2), '/') - 1) AS root_dir
                FROM 
                    search_index
                WHERE 
                    directory != '/'
                    AND directory LIKE '/%'
                    AND substr(directory, 2, instr(substr(directory, 2), '/') - 1) != ''
                ORDER BY 
                    root_dir
            """)
            
            root_dirs = await self.execute_query(root_dirs_query)
            
            for r in root_dirs:
                dir_path = f"/{r.root_dir}"
                if dir_path in seen_paths:
                    continue
                    
                seen_paths.add(dir_path)
                file_rows.append(
                    FileRow(
                        name=r.root_dir,
                        path=dir_path,
                        title=r.root_dir,
                        directory="/",
                        type="directory",
                        permalink=None,
                        entity_id=None,
                        content_type="directory",
                        updated_at=None
                    )
                )
        
        return file_rows
