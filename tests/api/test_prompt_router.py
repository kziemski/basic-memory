"""Tests for the prompt router endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import datetime
from dateutil import parser
from fastapi import FastAPI
from fastapi.testclient import TestClient

from basic_memory.api.routers.prompt_router import router
from basic_memory.schemas.memory import EntitySummary, GraphContext
from basic_memory.schemas.search import SearchItemType, SearchResult, SearchResponse
from basic_memory.schemas.prompt import ContinueConversationRequest, SearchPromptRequest


@pytest.fixture
def app():
    """Create a FastAPI app with the prompt router for testing."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_search_service():
    """Create a mock search_service for testing."""
    mock = AsyncMock()
    # Set up mock return values as needed
    return mock


@pytest.fixture
def mock_entity_service():
    """Create a mock entity_service for testing."""
    mock = AsyncMock()
    # Set up mock return values as needed
    return mock


@pytest.fixture
def mock_context_service():
    """Create a mock context_service for testing."""
    mock = AsyncMock()
    # Set up mock return values as needed
    return mock


@pytest.fixture
def mock_entity_repository():
    """Create a mock entity_repository for testing."""
    mock = AsyncMock()
    # Set up mock return values as needed
    return mock


@pytest.fixture
def mock_template_loader():
    """Create a mock template_loader for testing."""
    mock = AsyncMock()
    # Set up mock return values
    mock.render.return_value = "Mocked template rendering"
    return mock


def test_continue_conversation_endpoint(client, monkeypatch, mock_search_service, 
                                        mock_entity_service, mock_context_service, 
                                        mock_entity_repository, mock_template_loader):
    """Test the continue_conversation endpoint with a mock template loader."""
    # Create test data
    test_entity = EntitySummary(
        title="Test Entity",
        permalink="test/entity",
        type=SearchItemType.ENTITY,
        content="Test content",
        file_path="/path/to/test.md",
        created_at=datetime.datetime.now()
    )
    
    # Set up mock returns
    mock_context_service.build_context.return_value = {
        "primary_results": [test_entity],
        "related_results": [],
        "metadata": {}
    }
    
    # Patch the dependencies
    monkeypatch.setattr("basic_memory.api.routers.prompt_router.template_loader", mock_template_loader)
    monkeypatch.setattr("basic_memory.deps.get_search_service", lambda: mock_search_service)
    monkeypatch.setattr("basic_memory.deps.get_entity_service", lambda: mock_entity_service)
    monkeypatch.setattr("basic_memory.deps.get_context_service", lambda: mock_context_service)
    monkeypatch.setattr("basic_memory.deps.get_entity_repository", lambda: mock_entity_repository)
    
    # Test with topic
    response = client.post(
        "/prompt/continue-conversation",
        json={"topic": "test topic", "timeframe": "7d", "depth": 1, "related_items_limit": 2}
    )
    
    assert response.status_code == 200
    assert "prompt" in response.json()
    assert "context" in response.json()
    
    # Verify the template was rendered with the correct parameters
    mock_template_loader.render.assert_called_once()
    template_path = mock_template_loader.render.call_args[0][0]
    template_context = mock_template_loader.render.call_args[0][1]
    
    assert template_path == "prompts/continue_conversation.hbs"
    assert template_context["topic"] == "test topic"
    assert template_context["timeframe"] == "7d"
    
    # Reset mocks for next test
    mock_template_loader.render.reset_mock()
    
    # Test without topic - should get recent activity
    response = client.post(
        "/prompt/continue-conversation",
        json={"timeframe": "1d", "depth": 1, "related_items_limit": 2}
    )
    
    assert response.status_code == 200
    assert "prompt" in response.json()
    assert "context" in response.json()
    
    # Verify different context building flow was used for recent activity
    template_context = mock_template_loader.render.call_args[0][1]
    assert "Recent Activity" in template_context["topic"]
    assert template_context["timeframe"] == "1d"


def test_search_prompt_endpoint(client, monkeypatch, mock_search_service, 
                               mock_entity_service, mock_template_loader):
    """Test the search_prompt endpoint with a mock template loader."""
    # Create test data
    test_result = SearchResult(
        title="Test Result",
        type=SearchItemType.ENTITY,
        permalink="test/result",
        score=0.95,
        content="Test content",
        file_path="/path/to/test.md",
        metadata={}
    )
    
    # Set up mock returns
    mock_search_service.search.return_value = [test_result]
    
    # Patch the dependencies
    monkeypatch.setattr("basic_memory.api.routers.prompt_router.template_loader", mock_template_loader)
    monkeypatch.setattr("basic_memory.deps.get_search_service", lambda: mock_search_service)
    monkeypatch.setattr("basic_memory.deps.get_entity_service", lambda: mock_entity_service)
    monkeypatch.setattr("basic_memory.api.routers.utils.to_search_results", 
                       AsyncMock(return_value=[test_result]))
    
    # Test the endpoint
    response = client.post(
        "/prompt/search",
        json={"query": "test search", "timeframe": "7d"}
    )
    
    assert response.status_code == 200
    assert "prompt" in response.json()
    assert "context" in response.json()
    
    # Verify the template was rendered with the correct parameters
    mock_template_loader.render.assert_called_once()
    template_path = mock_template_loader.render.call_args[0][0]
    template_context = mock_template_loader.render.call_args[0][1]
    
    assert template_path == "prompts/search.hbs"
    assert template_context["query"] == "test search"
    assert template_context["timeframe"] == "7d"
    assert template_context["has_results"] is True
    assert len(template_context["results"]) == 1


def test_error_handling(client, monkeypatch, mock_search_service,
                       mock_entity_service, mock_context_service,
                       mock_entity_repository, mock_template_loader):
    """Test error handling in the endpoints."""
    # Simulate a template rendering error
    mock_template_loader.render.side_effect = Exception("Template error")
    
    # Patch the dependencies
    monkeypatch.setattr("basic_memory.api.routers.prompt_router.template_loader", mock_template_loader)
    monkeypatch.setattr("basic_memory.deps.get_search_service", lambda: mock_search_service)
    monkeypatch.setattr("basic_memory.deps.get_entity_service", lambda: mock_entity_service)
    monkeypatch.setattr("basic_memory.deps.get_context_service", lambda: mock_context_service)
    monkeypatch.setattr("basic_memory.deps.get_entity_repository", lambda: mock_entity_repository)
    
    # Test continue_conversation error handling
    response = client.post(
        "/prompt/continue-conversation",
        json={"topic": "test error", "timeframe": "7d"}
    )
    
    assert response.status_code == 500
    assert "detail" in response.json()
    assert "Template error" in response.json()["detail"]
    
    # Test search_prompt error handling
    response = client.post(
        "/prompt/search",
        json={"query": "test error", "timeframe": "7d"}
    )
    
    assert response.status_code == 500
    assert "detail" in response.json()
    assert "Template error" in response.json()["detail"]