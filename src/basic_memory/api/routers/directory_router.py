"""Router for directory tree operations."""

import os
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from basic_memory.deps import DirectoryServiceDep
from basic_memory.schemas.directory import DirectoryNodeSchema, DirectoryTreeSchema

router = APIRouter(prefix="/directory", tags=["directory"])


@router.get("/tree", response_model=DirectoryTreeSchema)
async def get_directory_tree(
    directory_service: DirectoryServiceDep,
    path: Optional[str] = Query("", description="Base path to start from"),
    depth: int = Query(1, description="Depth level to fetch (1 = just immediate children)"),
    include_files: bool = Query(True, description="Include files in results"),
):
    """Get hierarchical directory structure from the knowledge base.
    
    Params:
        path: Base path to start from (empty for root)
        depth: Which depth level to fetch (1 = immediate children)
        include_files: Whether to include files or just directories
    
    Returns:
        DirectoryTreeSchema containing nodes and metadata
    """
    # Get directory nodes from service
    nodes = await directory_service.get_directory_tree(path, depth, include_files)
    
    # Calculate parent path if not at root
    parent_path = None
    if path:
        parent_parts = path.rstrip('/').split('/')
        if len(parent_parts) > 1:
            parent_path = '/'.join(parent_parts[:-1])
            if not parent_path:
                parent_path = "/"  # Root when coming from first level directory
    
    # Convert to schema response
    return DirectoryTreeSchema(
        items=[DirectoryNodeSchema(**node.__dict__) for node in nodes],
        path=path or "/",
        depth=depth,
        parent_path=parent_path
    )