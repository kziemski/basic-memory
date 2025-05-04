"""Router for prompt-related operations.

This router is responsible for rendering various prompts using Liquid templates.
It centralizes all prompt formatting logic that was previously in the MCP prompts.
"""

from dateparser import parse
from fastapi import APIRouter, HTTPException, status
from loguru import logger

from basic_memory.api.routers.utils import to_graph_context, to_search_results
from basic_memory.api.template_loader import template_loader
from basic_memory.deps import (
    ContextServiceDep,
    EntityRepositoryDep,
    SearchServiceDep,
    EntityServiceDep,
)
from basic_memory.schemas.prompt import (
    ContinueConversationRequest,
    SearchPromptRequest,
    PromptResponse,
)
from basic_memory.schemas.search import SearchItemType, SearchQuery

router = APIRouter(prefix="/prompt", tags=["prompt"])


@router.post("/continue-conversation", response_model=PromptResponse)
async def continue_conversation(
    search_service: SearchServiceDep,
    entity_service: EntityServiceDep,
    context_service: ContextServiceDep,
    entity_repository: EntityRepositoryDep,
    request: ContinueConversationRequest,
) -> PromptResponse:
    """Generate a prompt for continuing a conversation.

    This endpoint takes a topic and/or timeframe and generates a prompt with
    relevant context from the knowledge base.

    Args:
        request: The request parameters

    Returns:
        Formatted continuation prompt with context
    """
    logger.info(
        f"Generating continue conversation prompt, topic: {request.topic}, timeframe: {request.timeframe}"
    )

    since = parse(request.timeframe)

    # Get data needed for template
    if request.topic:
        query = SearchQuery(text=request.topic, entity_types=[SearchItemType.ENTITY], after_date=request.timeframe)
        results = await search_service.search(query)
        search_results = await to_search_results(entity_service, results)

        # Build context from results
        contexts = []
        for result in search_results:
            if hasattr(result, "permalink") and result.permalink:
                context_results = await context_service.build_context(
                    result.permalink,
                    depth=request.depth,
                    since=since,
                    max_related=request.related_items_limit,
                )
                context = await to_graph_context(
                    context_results, entity_repository=entity_repository
                )

                if context.primary_results:
                    contexts.append(
                        {
                            "primary_results": context.primary_results[:1],
                            "related_results": context.related_results[:3],
                        }
                    )

        template_context = {
            "topic": request.topic,
            "timeframe": request.timeframe,
            "results": contexts,
            "has_results": len(contexts) > 0,
        }
    else:
        # If no topic, get recent activity
        context = await context_service.build_context(
            types=[SearchItemType.ENTITY],
            depth=request.depth,
            since=since,
            max_related=request.related_items_limit,
        )
        recent_context = await to_graph_context(context, entity_repository=entity_repository)

        template_context = {
            "topic": f"Recent Activity from ({request.timeframe})",
            "timeframe": request.timeframe,
            "results": [
                {
                    "primary_results": recent_context.primary_results[:5],
                    "related_results": recent_context.related_results[:2],
                }
            ],
            "has_results": len(recent_context.primary_results) > 0,
        }

    try:
        # Render template
        rendered_prompt = await template_loader.render(
            "prompts/continue_conversation.hbs", template_context
        )

        return PromptResponse(prompt=rendered_prompt, context=template_context)
    except Exception as e:
        logger.error(f"Error rendering continue conversation template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rendering prompt template: {str(e)}",
        )


@router.post("/search", response_model=PromptResponse)
async def search_prompt(
    search_service: SearchServiceDep,
    entity_service: EntityServiceDep,
    request: SearchPromptRequest,
    page: int = 1,
    page_size: int = 10,
) -> PromptResponse:
    """Generate a prompt for search results.

    This endpoint takes a search query and formats the results into a helpful
    prompt with context and suggestions.

    Args:
        request: The search parameters
        page: The page number for pagination
        page_size: The number of results per page, defaults to 10

    Returns:
        Formatted search results prompt with context
    """
    logger.info(f"Generating search prompt, query: {request.query}, timeframe: {request.timeframe}")

    limit = page_size
    offset = (page - 1) * page_size

    query = SearchQuery(text=request.query, after_date=request.timeframe)
    results = await search_service.search(query, limit=limit, offset=offset)
    search_results = await to_search_results(entity_service, results)

    template_context = {
        "query": request.query,
        "timeframe": request.timeframe,
        "results": results,
        "has_results": len(search_results) > 0,
        "result_count": len(search_results),
    }

    try:
        # Render template
        rendered_prompt = await template_loader.render("prompts/search.hbs", template_context)

        return PromptResponse(prompt=rendered_prompt, context=template_context)
    except Exception as e:
        logger.error(f"Error rendering search template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rendering prompt template: {str(e)}",
        )