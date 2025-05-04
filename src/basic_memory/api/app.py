"""FastAPI application for basic-memory knowledge graph API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exception_handlers import http_exception_handler
from loguru import logger

from basic_memory import __version__ as version
from basic_memory import db
from basic_memory.api.routers import (
    directory_router,
    knowledge,
    management,
    memory,
    project,
    resource,
    search,
    prompt_router,
)
from basic_memory.config import config as project_config
from basic_memory.services.initialization import initialize_app


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    """Lifecycle manager for the FastAPI app."""
    # Initialize database and file sync services
    app.state.watch_task = await initialize_app(project_config)

    # proceed with startup
    yield

    logger.info("Shutting down Basic Memory API")
    if app.state.watch_task:
        app.state.watch_task.cancel()  # pyright: ignore

    await db.shutdown_db()


# Initialize FastAPI app
app = FastAPI(
    title="Basic Memory API",
    description="Knowledge graph API for basic-memory",
    version=version,
    lifespan=lifespan,
)


# Include routers
app.include_router(knowledge.router)
app.include_router(management.router)
app.include_router(memory.router)
app.include_router(resource.router)
app.include_router(search.router)
app.include_router(project.router)
app.include_router(directory_router.router)
app.include_router(prompt_router.router)


@app.exception_handler(Exception)
async def exception_handler(request, exc):  # pragma: no cover
    logger.exception(
        "API unhandled exception",
        url=str(request.url),
        method=request.method,
        client=request.client.host if request.client else None,
        path=request.url.path,
        error_type=type(exc).__name__,
        error=str(exc),
    )
    return await http_exception_handler(request, HTTPException(status_code=500, detail=str(exc)))
