"""Router for project management."""

from fastapi import APIRouter

from basic_memory.deps import ProjectServiceDep
from basic_memory.schemas import ProjectInfoResponse
from basic_memory.schemas.project_info import (
    ProjectList,
    ProjectItem,
)

# Define the router - we'll combine stats and project operations
router = APIRouter(prefix="/project", tags=["project"])


# Get project information (moved from project_info_router.py)
@router.get("/info", response_model=ProjectInfoResponse)
async def get_project_info(
    project_service: ProjectServiceDep,
) -> ProjectInfoResponse:
    """Get comprehensive information about the current Basic Memory project."""
    return await project_service.get_project_info()


# List all available projects
@router.get("/projects", response_model=ProjectList)
async def list_projects(
    project_service: ProjectServiceDep,
) -> ProjectList:
    """List all configured projects.

    Returns:
        A list of all projects with metadata
    """
    projects_dict = project_service.projects
    default_project = project_service.default_project
    current_project = project_service.current_project

    project_items = []
    for name, path in projects_dict.items():
        project_items.append(
            ProjectItem(
                name=name,
                path=path,
                is_default=(name == default_project),
                is_current=(name == current_project),
            )
        )

    return ProjectList(
        projects=project_items,
        default_project=default_project,
        current_project=current_project,
    )
