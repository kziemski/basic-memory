"""Repository for directory tree operations."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Literal
import os

from sqlalchemy import text

from basic_memory.repository.repository import Repository

logger = logging.getLogger(__name__)


@dataclass
class DirectoryNode:
    """Directory or file node in the directory tree."""
    
    name: str
    path: str
    type: Literal["directory", "file"]
    title: str
    permalink: Optional[str] = None
    entity_id: Optional[int] = None
    entity_type: Optional[str] = None
    content_type: Optional[str] = None
    updated_at: Optional[str] = None
    
    @classmethod
    def create_directory(cls, name: str, path: str) -> "DirectoryNode":
        """Factory method for directory nodes."""
        return cls(
            name=name,
            path=path,
            type="directory",
            title=name,  
        )
        
    @classmethod
    def create_file(cls, name: str, path: str, permalink: str, **kwargs) -> "DirectoryNode":
        """Factory method for file nodes."""
        return cls(
            name=name,
            path=path, 
            type="file",
            title=kwargs.get("title", name),
            permalink=permalink,
            entity_id=kwargs.get("entity_id"),
            entity_type=kwargs.get("entity_type"),
            content_type=kwargs.get("content_type"),
            updated_at=kwargs.get("updated_at"),
        )


class DirectoryRepository(Repository):
    """Repository for directory structure operations."""

    def __init__(self, session_maker):
        # Initialize with a dummy model since we're just using the execute_query method
        super().__init__(session_maker, None)  # type: ignore

    async def get_directory_tree(
        self, base_path: str = "", include_files: bool = True
    ) -> List[DirectoryNode]:
        """Get directory tree at a specific depth level.

        Args:
            base_path: Base path to start from (empty for root)
            include_files: Whether to include files or just directories

        Returns:
            List of DirectoryNode objects representing the directory tree
        """
        logger.debug(f"Getting tree for base_path={base_path}")
        
        # List to store results
        result: List[DirectoryNode] = []
        
        try:
            # Normalize base path for consistency
            base_path = base_path.rstrip("/")
            
            # For empty test case detection
            count_query = text("SELECT COUNT(*) FROM search_index")
            count_result = await self.execute_query(count_query, use_query_options=False)
            entity_count = count_result.scalar_one()
            
            # Return empty list for empty database or invalid paths
            if entity_count == 0:
                return []
                
            # Set to track directory paths we've already seen
            directory_paths = set()
            
            # First, get all directories at this level using the directory column
            # This is much more efficient than pattern matching on file_path
            if base_path:
                # Get all direct child directories
                # For a path like "projects/notes", we want to find all directories 
                # where directory = "projects/notes/something" and extract "something"
                dir_query = text("""
                    SELECT DISTINCT
                        directory
                    FROM search_index
                    WHERE directory LIKE :dir_pattern AND directory != :base_dir
                    ORDER BY directory
                    LIMIT 1000
                """)
                dir_params = {
                    "dir_pattern": f"{base_path}/%", 
                    "base_dir": base_path
                }
                
                dir_results = await self.execute_query(dir_query, params=dir_params, use_query_options=False)
                
                # Process directory results
                for row in dir_results:
                    directory = row[0]
                    if not directory or not directory.startswith(f"{base_path}/"):
                        continue
                    
                    # Get the next directory component
                    # For "projects/notes/ideas", when base_path is "projects", 
                    # we want to extract "notes"
                    relative_path = directory[len(base_path) + 1:]  # +1 for the slash
                    if "/" in relative_path:
                        next_dir = relative_path.split("/")[0]
                        dir_path = f"{base_path}/{next_dir}"
                        
                        # Only add if we haven't seen this directory
                        if dir_path not in directory_paths:
                            directory_paths.add(dir_path)
                            result.append(DirectoryNode.create_directory(
                                name=next_dir,
                                path=dir_path
                            ))
            else:
                # Root level - get all top-level directories
                dir_query = text("""
                    SELECT DISTINCT
                        directory
                    FROM search_index
                    WHERE directory != '' AND directory IS NOT NULL
                    ORDER BY directory
                    LIMIT 1000
                """)
                
                dir_results = await self.execute_query(dir_query, use_query_options=False)
                
                # Process root level directory results
                for row in dir_results:
                    directory = row[0]
                    if not directory:
                        continue
                    
                    # Extract top level directory
                    top_dir = directory.split("/")[0]
                    
                    # Only add if we haven't seen this directory
                    if top_dir not in directory_paths:
                        directory_paths.add(top_dir)
                        result.append(DirectoryNode.create_directory(
                            name=top_dir,
                            path=top_dir
                        ))
            
            # If we need to include files, get all files at this level
            if include_files:
                if base_path:
                    # Get files directly under this path
                    file_query = text("""
                        SELECT 
                            si.file_path,
                            si.permalink,
                            si.id,
                            si.type AS entity_type,
                            e.content_type,
                            si.title,
                            si.updated_at
                        FROM search_index si
                        LEFT JOIN entity e ON si.id = e.id
                        WHERE si.directory = :base_dir
                        ORDER BY si.file_path
                        LIMIT 1000
                    """)
                    file_params = {"base_dir": base_path}
                else:
                    # Get files at root level
                    file_query = text("""
                        SELECT 
                            si.file_path,
                            si.permalink,
                            si.id,
                            si.type AS entity_type,
                            e.content_type,
                            si.title,
                            si.updated_at
                        FROM search_index si
                        LEFT JOIN entity e ON si.id = e.id
                        WHERE si.directory = '' OR si.directory IS NULL
                        ORDER BY si.file_path
                        LIMIT 1000
                    """)
                    file_params = {}
                
                file_results = await self.execute_query(file_query, params=file_params, use_query_options=False)
                
                # Process file results
                for row in file_results:
                    file_path, permalink, entity_id, entity_type, content_type, title, updated_at = row
                    
                    if not file_path:
                        continue
                    
                    # Get just the filename without the path
                    file_name = os.path.basename(file_path)
                    
                    # Format timestamp
                    updated_at_str = None
                    if updated_at:
                        if isinstance(updated_at, datetime):
                            updated_at_str = updated_at.isoformat()
                        else:
                            updated_at_str = str(updated_at)
                    
                    # Add file node
                    result.append(DirectoryNode.create_file(
                        name=file_name,
                        path=file_path,
                        permalink=permalink,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        content_type=content_type,
                        title=title or file_name,
                        updated_at=updated_at_str
                    ))
            
            # Sort: directories first, then alphabetically by name
            result.sort(key=lambda x: (0 if x.type == "directory" else 1, x.name.lower()))
            
            logger.debug(f"Found {len(result)} items in directory tree")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching directory tree: {e}")
            # Return empty list on error
            return []