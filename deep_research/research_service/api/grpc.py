"""gRPC service bindings for research service."""

from __future__ import annotations

from datetime import timezone
from typing import Any

import grpc
from google.protobuf import struct_pb2, timestamp_pb2
from google.protobuf.json_format import MessageToDict, ParseDict

from research_service.proto import research_service_pb2 as pb2
from research_service.proto import research_service_pb2_grpc as pb2_grpc
from research_service.schemas import (
    ResearchEventType,
    ResearchRequest,
    ResearchResponse,
    SubAgent,
    SubAgentsListResponse,
)
from research_service.service import ResearchService


def _struct_to_dict(struct: struct_pb2.Struct | None) -> dict[str, Any]:
    """Convert protobuf Struct to Python dict."""
    if not struct:
        return {}
    return MessageToDict(struct, preserving_proto_field_name=True)


def _dict_to_struct(data: dict[str, Any] | None) -> struct_pb2.Struct:
    """Convert Python dict to protobuf Struct."""
    struct = struct_pb2.Struct()
    ParseDict(data or {}, struct, ignore_unknown_fields=True)
    return struct


def _timestamp_from_datetime(dt):  # type: ignore[no-untyped-def]
    """Convert datetime to protobuf Timestamp."""
    stamp = timestamp_pb2.Timestamp()
    if dt is None:
        return stamp
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    stamp.FromDatetime(dt.astimezone(timezone.utc))
    return stamp


_PB_TO_EVENT_TYPE = {
    pb2.RESEARCH_EVENT_TYPE_RESEARCH_STARTED: ResearchEventType.RESEARCH_STARTED,
    pb2.RESEARCH_EVENT_TYPE_TOOL_CALL: ResearchEventType.TOOL_CALL,
    pb2.RESEARCH_EVENT_TYPE_TOOL_RESULT: ResearchEventType.TOOL_RESULT,
    pb2.RESEARCH_EVENT_TYPE_SUB_AGENT_DELEGATED: ResearchEventType.SUB_AGENT_DELEGATED,
    pb2.RESEARCH_EVENT_TYPE_SUB_AGENT_RESULT: ResearchEventType.SUB_AGENT_RESULT,
    pb2.RESEARCH_EVENT_TYPE_PROGRESS: ResearchEventType.PROGRESS,
    pb2.RESEARCH_EVENT_TYPE_REPORT_AVAILABLE: ResearchEventType.REPORT_AVAILABLE,
    pb2.RESEARCH_EVENT_TYPE_RESEARCH_COMPLETED: ResearchEventType.RESEARCH_COMPLETED,
    pb2.RESEARCH_EVENT_TYPE_ERROR: ResearchEventType.ERROR,
}
_EVENT_TYPE_TO_PB = {v: k for k, v in _PB_TO_EVENT_TYPE.items()}


def _event_to_proto(event) -> pb2.ResearchEvent:  # type: ignore[no-untyped-def]
    """Convert ResearchEvent schema to protobuf message."""
    return pb2.ResearchEvent(
        event_type=_EVENT_TYPE_TO_PB.get(event.event_type, pb2.RESEARCH_EVENT_TYPE_UNSPECIFIED),
        timestamp=_timestamp_from_datetime(event.timestamp),
        data=_dict_to_struct(event.data),
    )


def _request_from_proto(request: pb2.ResearchRequest) -> ResearchRequest:
    """Convert protobuf request to ResearchRequest schema."""
    return ResearchRequest(
        query=request.query,
        sub_agent=request.sub_agent or None,
        max_concurrent_research_units=request.max_concurrent_research_units or None,
        max_researcher_iterations=request.max_researcher_iterations or None,
        metadata=_struct_to_dict(request.metadata),
    )


def _response_to_proto(response: ResearchResponse) -> pb2.ResearchResponse:
    """Convert ResearchResponse schema to protobuf message."""
    return pb2.ResearchResponse(
        query=response.query,
        report=response.report or "",
        final_message=response.final_message or "",
        metadata=_dict_to_struct(response.metadata),
        completed_at=_timestamp_from_datetime(response.completed_at),
    )


def _sub_agent_to_proto(sub_agent: SubAgent) -> pb2.SubAgent:
    """Convert SubAgent schema to protobuf message."""
    return pb2.SubAgent(
        name=sub_agent.name,
        description=sub_agent.description,
        tools=sub_agent.tools,
    )


def _sub_agents_list_response_to_proto(
    response: SubAgentsListResponse,
) -> pb2.ListSubAgentsResponse:
    """Convert SubAgentsListResponse schema to protobuf message."""
    return pb2.ListSubAgentsResponse(
        sub_agents=[_sub_agent_to_proto(sub_agent) for sub_agent in response.sub_agents]
    )


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


class ResearchServiceServicer(pb2_grpc.ResearchServiceServicer):
    """Async gRPC servicer for research operations."""

    async def Research(self, request, context):  # type: ignore[override]
        """Execute research synchronously and return final result.

        Args:
            request: ResearchRequest protobuf message
            context: gRPC context

        Returns:
            ResearchResponse protobuf message
        """
        try:
            research_request = _request_from_proto(request)
            service = get_research_service()
            response = await service.execute_research_sync(research_request)
            return _response_to_proto(response)
        except Exception as e:
            await context.abort(grpc.StatusCode.INTERNAL, f"Research execution failed: {str(e)}")

    async def ResearchStream(self, request, context):  # type: ignore[override]
        """Execute research and stream events.

        Args:
            request: ResearchRequest protobuf message
            context: gRPC context

        Yields:
            ResearchEvent protobuf messages
        """
        try:
            research_request = _request_from_proto(request)
            service = get_research_service()
            async for event in service.execute_research(research_request):
                yield _event_to_proto(event)
        except Exception as e:
            await context.abort(grpc.StatusCode.INTERNAL, f"Research stream failed: {str(e)}")

    async def ListSubAgents(self, request, context):  # type: ignore[override]
        """Get list of available sub-agents.

        Args:
            request: ListSubAgentsRequest protobuf message
            context: gRPC context

        Returns:
            ListSubAgentsResponse protobuf message
        """
        try:
            service = get_research_service()
            response = service.get_sub_agents()
            return _sub_agents_list_response_to_proto(response)
        except Exception as e:
            await context.abort(
                grpc.StatusCode.INTERNAL, f"Failed to retrieve sub-agents: {str(e)}"
            )


def build_grpc_server() -> grpc.aio.Server:
    """Create a configured gRPC server.

    Returns:
        Configured gRPC server instance
    """
    server = grpc.aio.server()
    pb2_grpc.add_ResearchServiceServicer_to_server(ResearchServiceServicer(), server)
    return server


__all__ = ["ResearchServiceServicer", "build_grpc_server"]

