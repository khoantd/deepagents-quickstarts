"""REST API router for research service."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from research_service.schemas import ResearchEvent, ResearchRequest, ResearchResponse
from research_service.service import ResearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["Research"])


def get_research_service() -> ResearchService:
    """Get the research service instance.

    Returns:
        ResearchService instance
    """
    # Import here to avoid circular imports
    import sys
    from pathlib import Path

    # Add parent directory to path to import agent
    parent_dir = Path(__file__).resolve().parent.parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    from agent import agent

    return ResearchService(agent)


@router.post(
    "",
    response_model=ResearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Synchronous Research",
    response_description="The final research report and metadata.",
)
async def research_endpoint(
    request: ResearchRequest,
) -> ResearchResponse:
    """Execute research synchronously and return final result.

    Args:
        request: Research request with query and optional parameters

    Returns:
        ResearchResponse with final report and metadata
    """
    try:
        service = get_research_service()
        return await service.execute_research_sync(request)
    except Exception as e:
        logger.exception("Error in research endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research execution failed: {str(e)}",
        ) from e


@router.post(
    "/stream",
    summary="Stream Research Events",
    response_description="Server-Sent Events (SSE) stream of research progress and results.",
)
async def research_stream_endpoint(
    request: ResearchRequest,
) -> EventSourceResponse:
    """Execute research and stream events via Server-Sent Events (SSE).

    Args:
        request: Research request with query and optional parameters

    Returns:
        EventSourceResponse streaming ResearchEvent objects
    """
    service = get_research_service()

    async def event_generator():
        """Generate SSE events from research service."""
        try:
            async for event in service.execute_research(request):
                # Format event as SSE
                event_data = {
                    "event_type": event.event_type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data,
                }
                yield {
                    "event": "research_event",
                    "data": json.dumps(event_data),
                }
        except Exception as e:
            logger.exception("Error in research stream")
            error_event = {
                "event_type": "error",
                "timestamp": ResearchEvent().timestamp.isoformat(),
                "data": {"error": str(e)},
            }
            yield {
                "event": "research_event",
                "data": json.dumps(error_event),
            }

    return EventSourceResponse(event_generator())


@router.get("/healthz", tags=["Health"])
async def healthcheck() -> dict[str, str]:
    """Lightweight readiness probe.

    Returns:
        Health status
    """
    return {"status": "ok"}

