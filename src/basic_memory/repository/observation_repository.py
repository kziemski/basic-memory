"""Repository for managing Observation objects."""

from typing import Dict, List, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from basic_memory.models import Observation
from basic_memory.repository.repository import Repository


class ObservationRepository(Repository[Observation]):
    """Repository for Observation model with memory-specific operations."""

    def __init__(self, session_maker: async_sessionmaker):
        super().__init__(session_maker, Observation)

    async def find_by_entity(self, entity_id: int) -> Sequence[Observation]:
        """Find all observations for a specific entity."""
        query = select(Observation).filter(Observation.entity_id == entity_id)
        result = await self.execute_query(query)
        return result.scalars().all()

    async def find_by_context(self, context: str) -> Sequence[Observation]:
        """Find observations with a specific context."""
        query = select(Observation).filter(Observation.context == context)
        result = await self.execute_query(query)
        return result.scalars().all()

    async def find_by_category(self, category: str) -> Sequence[Observation]:
        """Find observations with a specific context."""
        query = select(Observation).filter(Observation.category == category)
        result = await self.execute_query(query)
        return result.scalars().all()

    async def observation_categories(self) -> Sequence[str]:
        """Return a list of all observation categories."""
        query = select(Observation.category).distinct()
        result = await self.execute_query(query, use_query_options=False)
        return result.scalars().all()
        
    async def find_by_entities(self, entity_ids: List[int]) -> Dict[int, List[Observation]]:
        """Find all observations for multiple entities in a single query.
        
        Args:
            entity_ids: List of entity IDs to fetch observations for
            
        Returns:
            Dictionary mapping entity_id to list of observations
        """
        if not entity_ids:
            return {}
            
        # Query observations for all entities in the list
        query = select(Observation).filter(Observation.entity_id.in_(entity_ids))
        result = await self.execute_query(query)
        observations = result.scalars().all()
        
        # Group observations by entity_id
        observations_by_entity = {}
        for obs in observations:
            if obs.entity_id not in observations_by_entity:
                observations_by_entity[obs.entity_id] = []
            observations_by_entity[obs.entity_id].append(obs)
            
        return observations_by_entity
