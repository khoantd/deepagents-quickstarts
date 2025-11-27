"""Pydantic schemas for research service requests and responses."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResearchEventType(str, Enum):
    """Types of research events that can be streamed."""

    RESEARCH_STARTED = "research_started"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SUB_AGENT_DELEGATED = "sub_agent_delegated"
    SUB_AGENT_RESULT = "sub_agent_result"
    PROGRESS = "progress"
    REPORT_AVAILABLE = "report_available"
    RESEARCH_COMPLETED = "research_completed"
    ERROR = "error"


class ResearchRequest(BaseModel):
    """Request schema for initiating a research task."""

    query: str = Field(..., description="The research question or topic to investigate")
    sub_agent: str | None = Field(
        default=None,
        description="Optional sub-agent name to use (research-agent, news-researcher, technical-docs-researcher, code-analyst)",
    )
    max_concurrent_research_units: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Maximum number of parallel sub-agents (default: 3)",
    )
    max_researcher_iterations: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Maximum number of delegation rounds (default: 3)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata to attach to the research request",
    )


class ResearchEvent(BaseModel):
    """Schema for streaming research events."""

    event_type: ResearchEventType = Field(..., description="Type of event")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific data payload",
    )


class ResearchResponse(BaseModel):
    """Final response schema for completed research."""

    query: str = Field(..., description="The original research query")
    report: str | None = Field(
        default=None,
        description="Final research report content (from /final_report.md if available)",
    )
    final_message: str | None = Field(
        default=None,
        description="Final agent message if report is not available",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Research metadata including tool calls, sub-agents used, etc.",
    )
    completed_at: datetime = Field(default_factory=datetime.now, description="Completion timestamp")

