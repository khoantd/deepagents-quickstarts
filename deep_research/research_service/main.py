"""FastAPI application entrypoint for the research service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from research_service.api import rest
from research_service.settings import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: D401
    """Manage resources on startup/shutdown."""

    logger.info("Starting %s", app.title)
    yield
    logger.info("Stopping %s", app.title)


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    settings = get_settings()
    fastapi_app = FastAPI(
        title=settings.app_name,
        description="Deep Research Service API for orchestrating web research agents.",
        version="0.1.0",
        contact={
            "name": "Deep Agents Team",
            "url": "https://github.com/langchain-ai/deepagents",
        },
        license_info={
            "name": "MIT",
        },
        lifespan=lifespan,
    )
    fastapi_app.include_router(rest.router)

    @fastapi_app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all unhandled exceptions."""
        logger.exception("Unhandled exception: %s", exc, exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Internal server error: {str(exc)}"},
        )

    @fastapi_app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle request validation errors."""
        logger.warning("Validation error: %s", exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    return fastapi_app


app = create_app()

