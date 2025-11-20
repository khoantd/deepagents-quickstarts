"""FastAPI application entrypoint for the thread service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .settings import get_settings
from .api import rest

logger = logging.getLogger(__name__)


@asynccontextmanager
def lifespan(app: FastAPI):  # noqa: D401
    """Manage resources on startup/shutdown."""

    logger.info("Starting %s", app.title)
    yield
    logger.info("Stopping %s", app.title)


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    settings = get_settings()
    fastapi_app = FastAPI(title=settings.app_name, lifespan=lifespan)
    fastapi_app.include_router(rest.router)

    @fastapi_app.get("/healthz", tags=["Health"])
    async def healthcheck() -> dict[str, str]:
        """Lightweight readiness probe."""

        return {"status": "ok"}

    return fastapi_app


app = create_app()
