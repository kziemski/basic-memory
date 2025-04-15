"""Router for directory tree operations."""

from fastapi import APIRouter, Query

from basic_memory.deps import DirectoryServiceDep
from basic_memory.schemas.directory import DirectoryTree, DirectoryTreeResponse

router = APIRouter(prefix="/directory", tags=["directory"])


@router.get("/tree", response_model=DirectoryTreeResponse)
async def get_directory_tree(
    directory_service: DirectoryServiceDep,
    path: str = Query("", description="Directory path"),
    include_files: bool = Query(True, description="Include files in results"),
    depth: int = Query(1, description="Depth of directory traversal"),
):
    """Get hierarchical directory structure from the knowledge base.
    
    Params:
        path: Base path to start from (empty for root)
        include_files: Whether to include files or just directories
        depth: How deep to traverse the directory tree
    
    Returns:
        DirectoryTreeResponse containing nodes and base path
    """
    # Get directory nodes from service
    nodes = await directory_service.list_files(path, include_files, depth)
    
    # Return in the format expected by the client
    return DirectoryTreeResponse(
        base_path=path or "/",
        items=nodes
    )

    