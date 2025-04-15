"""Router for directory tree operations."""

from typing import List

from fastapi import APIRouter

from basic_memory.deps import DirectoryServiceDep
from basic_memory.schemas.directory import DirectoryNode

router = APIRouter(prefix="/directory", tags=["directory"])


@router.get("/tree", response_model=List[DirectoryNode])
async def get_directory_tree(
    directory_service: DirectoryServiceDep,
):
    """Get hierarchical directory structure from the knowledge base.

    Returns:
        list of DirectoryNode containing files and paths
    """
    # Get directory nodes from service
    nodes = await directory_service.get_directory_tree()

    # Return in the format expected by the client
    return nodes
