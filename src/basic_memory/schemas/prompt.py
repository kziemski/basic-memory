"""Request and response schemas for prompt-related operations."""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field

from basic_memory.schemas.base import TimeFrame
from basic_memory.schemas.memory import EntitySummary, ObservationSummary, RelationSummary


class PromptContextItem(BaseModel):
    """Container for primary and related results to render in a prompt."""
    
    primary_results: List[EntitySummary]
    related_results: List[EntitySummary | ObservationSummary | RelationSummary]


class ContinueConversationRequest(BaseModel):
    """Request for generating a continue conversation prompt.
    
    Used to provide context for continuing a conversation on a specific topic
    or with recent activity from a given timeframe.
    """
    
    topic: Optional[str] = Field(None, description="Topic or keyword to search for")
    timeframe: Optional[TimeFrame] = Field(None, description="How far back to look for activity (e.g. '1d', '1 week')")
    depth: int = Field(1, description="How many relationship 'hops' to follow when building context")
    related_items_limit: int = Field(2, description="Maximum number of related items to include in context")


class SearchPromptRequest(BaseModel):
    """Request for generating a search results prompt.
    
    Used to format search results into a prompt with context and suggestions.
    """
    
    query: str = Field(..., description="The search query text")
    timeframe: Optional[TimeFrame] = Field(None, description="Optional timeframe to limit results (e.g. '1d', '1 week')")


class PromptResponse(BaseModel):
    """Response containing the rendered prompt.
    
    Includes both the rendered prompt text and the context that was used
    to render it, for potential client-side use.
    """
    
    prompt: str = Field(..., description="The rendered prompt text")
    context: Dict[str, Any] = Field(..., description="The context used to render the prompt")