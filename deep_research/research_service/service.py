"""Core service logic for executing research agent and streaming events."""

import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator

from langchain_core.messages import HumanMessage

from research_service.schemas import ResearchEvent, ResearchEventType, ResearchRequest, ResearchResponse

logger = logging.getLogger(__name__)


class ResearchService:
    """Service for executing research agent and streaming events."""

    def __init__(self, agent):
        """Initialize the research service with an agent instance.

        Args:
            agent: The LangGraph agent instance from agent.py
        """
        self.agent = agent

    async def execute_research(
        self,
        request: ResearchRequest,
    ) -> AsyncIterator[ResearchEvent]:
        """Execute research and stream events as they occur.

        Args:
            request: Research request with query and optional parameters

        Yields:
            ResearchEvent objects as research progresses
        """
        # Yield research started event
        yield ResearchEvent(
            event_type=ResearchEventType.RESEARCH_STARTED,
            data={"query": request.query, "metadata": request.metadata},
        )

        try:
            # Prepare agent input
            messages = [HumanMessage(content=request.query)]

            # Configure agent if custom limits provided
            config = {}
            if request.max_concurrent_research_units is not None:
                config["max_concurrent_research_units"] = request.max_concurrent_research_units
            if request.max_researcher_iterations is not None:
                config["max_researcher_iterations"] = request.max_researcher_iterations

            # Stream agent events
            async for event in self.agent.astream_events(
                messages,
                config=config if config else None,
                version="v2",
            ):
                event_name = event.get("event")
                event_data = event.get("data", {})

                # Handle different event types
                if event_name == "on_chain_start":
                    # Tool call started
                    if "tool" in event_data.get("name", "").lower():
                        tool_name = event_data.get("name", "")
                        yield ResearchEvent(
                            event_type=ResearchEventType.TOOL_CALL,
                            data={
                                "tool": tool_name,
                                "input": event_data.get("input", {}),
                            },
                        )

                elif event_name == "on_chain_end":
                    # Tool call completed
                    if "tool" in event_data.get("name", "").lower():
                        tool_name = event_data.get("name", "")
                        output = event_data.get("output", "")
                        yield ResearchEvent(
                            event_type=ResearchEventType.TOOL_RESULT,
                            data={
                                "tool": tool_name,
                                "output": str(output)[:1000],  # Truncate long outputs
                            },
                        )

                elif event_name == "on_chain_stream":
                    # Progress updates
                    if event_data.get("chunk"):
                        yield ResearchEvent(
                            event_type=ResearchEventType.PROGRESS,
                            data={"message": str(event_data.get("chunk", ""))[:500]},
                        )

            # After streaming completes, try to extract final report
            # The agent writes to /final_report.md, so we check the file system
            report_content = None
            final_message = None

            # Try to read from /final_report.md if it exists
            # Note: This assumes the agent writes to a known location
            # In a real deployment, this might be in a temp directory or workspace
            report_path = Path("/final_report.md")
            if report_path.exists():
                try:
                    report_content = report_path.read_text(encoding="utf-8")
                    yield ResearchEvent(
                        event_type=ResearchEventType.REPORT_AVAILABLE,
                        data={"path": str(report_path)},
                    )
                except Exception as e:
                    logger.warning(f"Failed to read report file: {e}")

            # Yield completion event
            yield ResearchEvent(
                event_type=ResearchEventType.RESEARCH_COMPLETED,
                data={
                    "report": report_content,
                    "final_message": final_message,
                },
            )

        except Exception as e:
            logger.exception("Error during research execution")
            yield ResearchEvent(
                event_type=ResearchEventType.ERROR,
                data={"error": str(e)},
            )

    async def execute_research_sync(
        self,
        request: ResearchRequest,
    ) -> ResearchResponse:
        """Execute research synchronously and return final result.

        Args:
            request: Research request with query and optional parameters

        Returns:
            ResearchResponse with final report and metadata
        """
        report_content = None
        final_message = None
        metadata = {"tool_calls": [], "sub_agents": []}

        try:
            # Collect all events
            events = []
            async for event in self.execute_research(request):
                events.append(event)

                # Track tool calls and sub-agents
                if event.event_type == ResearchEventType.TOOL_CALL:
                    metadata["tool_calls"].append(event.data.get("tool"))
                elif event.event_type == ResearchEventType.SUB_AGENT_DELEGATED:
                    metadata["sub_agents"].append(event.data.get("sub_agent"))

            # Extract final report from completion event
            for event in reversed(events):
                if event.event_type == ResearchEventType.RESEARCH_COMPLETED:
                    report_content = event.data.get("report")
                    final_message = event.data.get("final_message")
                    break
                elif event.event_type == ResearchEventType.REPORT_AVAILABLE:
                    # Try to read the report file
                    report_path = event.data.get("path", "/final_report.md")
                    try:
                        report_content = Path(report_path).read_text(encoding="utf-8")
                    except Exception as e:
                        logger.warning(f"Failed to read report from {report_path}: {e}")

            # If no report found, use final message
            if not report_content and final_message:
                report_content = final_message

            return ResearchResponse(
                query=request.query,
                report=report_content,
                final_message=final_message,
                metadata=metadata,
            )

        except Exception as e:
            logger.exception("Error in synchronous research execution")
            return ResearchResponse(
                query=request.query,
                report=None,
                final_message=f"Error: {str(e)}",
                metadata={"error": str(e)},
            )

