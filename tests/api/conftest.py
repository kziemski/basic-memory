"""Tests for knowledge graph API routes."""

from typing import AsyncGenerator

import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from basic_memory.deps import get_project_config, get_engine_factory


@pytest_asyncio.fixture
async def app(test_config, engine_factory) -> FastAPI:
    """Create FastAPI test application."""
    from basic_memory.api.app import app

    app.dependency_overrides[get_project_config] = lambda: test_config
    app.dependency_overrides[get_engine_factory] = lambda: engine_factory
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create client using ASGI transport - same as CLI will use."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
