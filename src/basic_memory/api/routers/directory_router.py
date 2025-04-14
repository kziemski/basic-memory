"""Router for directory tree operations."""

from fastapi import APIRouter, Query

from basic_memory.deps import DirectoryServiceDep
from basic_memory.schemas.directory import DirectoryTree

router = APIRouter(prefix="/directory", tags=["directory"])


@router.get("/tree", response_model=DirectoryTree)
async def get_directory_tree(
    directory_service: DirectoryServiceDep,
    path: str = Query("", description="Directory path"),
    include_files: bool = Query(True, description="Include files in results"),
):
    """Get hierarchical directory structure from the knowledge base.
    
    Params:
        path: Base path to start from (empty for root)
        include_files: Whether to include files or just directories
    
    Returns:
        DirectoryTreeSchema containing nodes and metadata
    """
    # Get directory nodes from service
    nodes = await directory_service.list_files(path, include_files)

    