"""Router for directory tree operations."""

from fastapi import APIRouter

from basic_memory.deps import DirectoryServiceDep
from basic_memory.schemas.directory import DirectoryNode

router = APIRouter(prefix="/directory", tags=["directory"])


@router.get("/tree", response_model=DirectoryNode)
async def get_directory_tree(
    directory_service: DirectoryServiceDep,
):
    """Get hierarchical directory structure from the knowledge base.

    Returns:
        DirectoryNode representing the root of the hierarchical tree structure
    """
    # Get a hierarchical directory tree
    tree = await directory_service.get_directory_tree()

    # Return the hierarchical tree
    return tree
