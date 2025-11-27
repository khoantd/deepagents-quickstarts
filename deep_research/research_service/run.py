"""Run both FastAPI and gRPC servers together."""

from __future__ import annotations

import asyncio
import logging

import uvicorn

from research_service.api.grpc import build_grpc_server
from research_service.main import app
from research_service.settings import get_settings

logger = logging.getLogger(__name__)


async def main() -> None:
    """Start both HTTP and gRPC servers."""
    settings = get_settings()
    grpc_server = build_grpc_server()
    grpc_server.add_insecure_port(f"{settings.grpc_host}:{settings.grpc_port}")

    uvicorn_config = uvicorn.Config(
        app,
        host=settings.http_host,
        port=settings.http_port,
        reload=settings.enable_reload,
        log_level="info",
    )
    uvicorn_server = uvicorn.Server(uvicorn_config)

    async def _serve_grpc() -> None:
        await grpc_server.start()
        logger.info("gRPC server listening on %s:%s", settings.grpc_host, settings.grpc_port)
        await grpc_server.wait_for_termination()

    async def _serve_http() -> None:
        logger.info("FastAPI server listening on %s:%s", settings.http_host, settings.http_port)
        await uvicorn_server.serve()

    await asyncio.gather(_serve_grpc(), _serve_http())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

