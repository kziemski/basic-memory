"""Project management service for Basic Memory."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from loguru import logger
from sqlalchemy import text

from basic_memory.config import ConfigManager, config, ProjectConfig, app_config
from basic_memory.repository.project_repository import ProjectRepository
from basic_memory.schemas import (
    ActivityMetrics,
    ProjectInfoResponse,
    ProjectStatistics,
    SystemStatus,
)
from basic_memory.sync.watch_service import WATCH_STATUS_JSON


class ProjectService:
    """Service for managing Basic Memory projects."""

    def __init__(self, repository: Optional[ProjectRepository] = None):
        """Initialize the project service."""
        super().__init__()
        self.config_manager = ConfigManager()
        self.repository = repository

    @property
    def projects(self) -> Dict[str, str]:
        """Get all configured projects.

        Returns:
            Dict mapping project names to their file paths
        """
        return self.config_manager.projects

    @property
    def default_project(self) -> str:
        """Get the name of the default project.

        Returns:
            The name of the default project
        """
        return self.config_manager.default_project

    @property
    def current_project(self) -> str:
        """Get the name of the currently active project.

        Returns:
            The name of the current project
        """
        return os.environ.get("BASIC_MEMORY_PROJECT", self.config_manager.default_project)

    def add_project(self, name: str, path: str) -> None:
        """Add a new project to the configuration.

        Args:
            name: The name of the project
            path: The file path to the project directory

        Raises:
            ValueError: If the project already exists
        """
        # Resolve to absolute path
        resolved_path = os.path.abspath(os.path.expanduser(path))
        self.config_manager.add_project(name, resolved_path)
        logger.info(f"Project '{name}' added at {resolved_path}")

    def remove_project(self, name: str) -> None:
        """Remove a project from configuration.

        Args:
            name: The name of the project to remove

        Raises:
            ValueError: If the project doesn't exist or is the default project
        """
        self.config_manager.remove_project(name)
        logger.info(f"Project '{name}' removed from configuration")

    def switch_project(self, name: str) -> ProjectConfig:
        """Switch to a different project.

        Args:
            name: The name of the project to switch to

        Raises:
            ValueError: If the project doesn't exist
        """
        if name not in self.config_manager.projects:
            raise ValueError(f"Project '{name}' not found")

        # Activate it for the current session by setting the environment variable
        os.environ["BASIC_MEMORY_PROJECT"] = name

        # Reload configuration to apply the change
        from importlib import reload

        from basic_memory import config as config_module

        reload(config_module)

        # Reload configuration to apply the change
        logger.info(f"Switched to project: {name}")

        return config_module.config

    def set_default_project(self, name: str) -> None:
        """Set the default project.

        Args:
            name: The name of the project to set as default

        Raises:
            ValueError: If the project doesn't exist
        """
        # Set the default project
        self.config_manager.set_default_project(name)
        self.switch_project(name)

        logger.info(f"Project '{name}' set as default")

    async def get_project_info(self) -> ProjectInfoResponse:
        """Get comprehensive information about the current Basic Memory project.

        Returns:
            Comprehensive project information and statistics
        """
        if not self.repository:
            raise ValueError("Repository is required for get_project_info")

        # Get statistics
        statistics = await self.get_statistics()

        # Get activity metrics
        activity = await self.get_activity_metrics()

        # Get system status
        system = self.get_system_status()

        # Get project configuration information
        project_name = config.project
        project_path = str(config.home)
        available_projects = self.config_manager.projects
        default_project = self.config_manager.default_project

        # Construct the response
        return ProjectInfoResponse(
            project_name=project_name,
            project_path=project_path,
            available_projects=available_projects,
            default_project=default_project,
            statistics=statistics,
            activity=activity,
            system=system,
        )

    async def get_statistics(self) -> ProjectStatistics:
        """Get statistics about the current project."""
        if not self.repository:
            raise ValueError("Repository is required for get_statistics")

        # Get basic counts
        entity_count_result = await self.repository.execute_query(
            text("SELECT COUNT(*) FROM entity")
        )
        total_entities = entity_count_result.scalar() or 0

        observation_count_result = await self.repository.execute_query(
            text("SELECT COUNT(*) FROM observation")
        )
        total_observations = observation_count_result.scalar() or 0

        relation_count_result = await self.repository.execute_query(
            text("SELECT COUNT(*) FROM relation")
        )
        total_relations = relation_count_result.scalar() or 0

        unresolved_count_result = await self.repository.execute_query(
            text("SELECT COUNT(*) FROM relation WHERE to_id IS NULL")
        )
        total_unresolved = unresolved_count_result.scalar() or 0

        # Get entity counts by type
        entity_types_result = await self.repository.execute_query(
            text("SELECT entity_type, COUNT(*) FROM entity GROUP BY entity_type")
        )
        entity_types = {row[0]: row[1] for row in entity_types_result.fetchall()}

        # Get observation counts by category
        category_result = await self.repository.execute_query(
            text("SELECT category, COUNT(*) FROM observation GROUP BY category")
        )
        observation_categories = {row[0]: row[1] for row in category_result.fetchall()}

        # Get relation counts by type
        relation_types_result = await self.repository.execute_query(
            text("SELECT relation_type, COUNT(*) FROM relation GROUP BY relation_type")
        )
        relation_types = {row[0]: row[1] for row in relation_types_result.fetchall()}

        # Find most connected entities (most outgoing relations)
        connected_result = await self.repository.execute_query(
            text("""
            SELECT e.id, e.title, e.permalink, COUNT(r.id) AS relation_count, file_path
            FROM entity e
            JOIN relation r ON e.id = r.from_id
            GROUP BY e.id
            ORDER BY relation_count DESC
            LIMIT 10
        """)
        )
        most_connected = [
            {
                "id": row[0],
                "title": row[1],
                "permalink": row[2],
                "relation_count": row[3],
                "file_path": row[4],
            }
            for row in connected_result.fetchall()
        ]

        # Count isolated entities (no relations)
        isolated_result = await self.repository.execute_query(
            text("""
            SELECT COUNT(e.id)
            FROM entity e
            LEFT JOIN relation r1 ON e.id = r1.from_id
            LEFT JOIN relation r2 ON e.id = r2.to_id
            WHERE r1.id IS NULL AND r2.id IS NULL
        """)
        )
        isolated_count = isolated_result.scalar() or 0

        return ProjectStatistics(
            total_entities=total_entities,
            total_observations=total_observations,
            total_relations=total_relations,
            total_unresolved_relations=total_unresolved,
            entity_types=entity_types,
            observation_categories=observation_categories,
            relation_types=relation_types,
            most_connected_entities=most_connected,
            isolated_entities=isolated_count,
        )

    async def get_activity_metrics(self) -> ActivityMetrics:
        """Get activity metrics for the current project."""
        if not self.repository:
            raise ValueError("Repository is required for get_activity_metrics")

        # Get recently created entities
        created_result = await self.repository.execute_query(
            text("""
            SELECT id, title, permalink, entity_type, created_at, file_path 
            FROM entity
            ORDER BY created_at DESC
            LIMIT 10
        """)
        )
        recently_created = [
            {
                "id": row[0],
                "title": row[1],
                "permalink": row[2],
                "entity_type": row[3],
                "created_at": row[4],
                "file_path": row[5],
            }
            for row in created_result.fetchall()
        ]

        # Get recently updated entities
        updated_result = await self.repository.execute_query(
            text("""
            SELECT id, title, permalink, entity_type, updated_at, file_path 
            FROM entity
            ORDER BY updated_at DESC
            LIMIT 10
        """)
        )
        recently_updated = [
            {
                "id": row[0],
                "title": row[1],
                "permalink": row[2],
                "entity_type": row[3],
                "updated_at": row[4],
                "file_path": row[5],
            }
            for row in updated_result.fetchall()
        ]

        # Get monthly growth over the last 6 months
        # Calculate the start of 6 months ago
        now = datetime.now()
        six_months_ago = datetime(
            now.year - (1 if now.month <= 6 else 0), ((now.month - 6) % 12) or 12, 1
        )

        # Query for monthly entity creation
        entity_growth_result = await self.repository.execute_query(
            text(f"""
            SELECT 
                strftime('%Y-%m', created_at) AS month,
                COUNT(*) AS count
            FROM entity
            WHERE created_at >= '{six_months_ago.isoformat()}'
            GROUP BY month
            ORDER BY month
        """)
        )
        entity_growth = {row[0]: row[1] for row in entity_growth_result.fetchall()}

        # Query for monthly observation creation
        observation_growth_result = await self.repository.execute_query(
            text(f"""
            SELECT 
                strftime('%Y-%m', created_at) AS month,
                COUNT(*) AS count
            FROM observation
            INNER JOIN entity ON observation.entity_id = entity.id
            WHERE entity.created_at >= '{six_months_ago.isoformat()}'
            GROUP BY month
            ORDER BY month
        """)
        )
        observation_growth = {row[0]: row[1] for row in observation_growth_result.fetchall()}

        # Query for monthly relation creation
        relation_growth_result = await self.repository.execute_query(
            text(f"""
            SELECT 
                strftime('%Y-%m', created_at) AS month,
                COUNT(*) AS count
            FROM relation
            INNER JOIN entity ON relation.from_id = entity.id
            WHERE entity.created_at >= '{six_months_ago.isoformat()}'
            GROUP BY month
            ORDER BY month
        """)
        )
        relation_growth = {row[0]: row[1] for row in relation_growth_result.fetchall()}

        # Combine all monthly growth data
        monthly_growth = {}
        for month in set(
            list(entity_growth.keys())
            + list(observation_growth.keys())
            + list(relation_growth.keys())
        ):
            monthly_growth[month] = {
                "entities": entity_growth.get(month, 0),
                "observations": observation_growth.get(month, 0),
                "relations": relation_growth.get(month, 0),
                "total": (
                    entity_growth.get(month, 0)
                    + observation_growth.get(month, 0)
                    + relation_growth.get(month, 0)
                ),
            }

        return ActivityMetrics(
            recently_created=recently_created,
            recently_updated=recently_updated,
            monthly_growth=monthly_growth,
        )

    def get_system_status(self) -> SystemStatus:
        """Get system status information."""
        import basic_memory

        # Get database information
        db_path = app_config.database_path
        db_size = db_path.stat().st_size if db_path.exists() else 0
        db_size_readable = f"{db_size / (1024 * 1024):.2f} MB"

        # Get watch service status if available
        watch_status = None
        watch_status_path = Path.home() / ".basic-memory" / WATCH_STATUS_JSON
        if watch_status_path.exists():
            try:
                watch_status = json.loads(watch_status_path.read_text(encoding="utf-8"))
            except Exception:  # pragma: no cover
                pass

        return SystemStatus(
            version=basic_memory.__version__,
            database_path=str(db_path),
            database_size=db_size_readable,
            watch_status=watch_status,
            timestamp=datetime.now(),
        )