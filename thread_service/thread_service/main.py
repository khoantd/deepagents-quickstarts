"""FastAPI application entrypoint for the thread service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .settings import get_settings
from .api import auth, rest

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
    fastapi_app = FastAPI(title=settings.app_name, lifespan=lifespan)
    fastapi_app.include_router(auth.router)
    fastapi_app.include_router(rest.router)

    @fastapi_app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all unhandled exceptions."""
        logger.exception("Unhandled exception: %s", exc, exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Internal server error: {str(exc)}"},
        )

    @fastapi_app.get("/healthz", tags=["Health"])
    async def healthcheck() -> dict[str, str]:
        """Lightweight readiness probe."""

        return {"status": "ok"}

    return fastapi_app


app = create_app()
