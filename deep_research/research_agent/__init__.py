"""Deep Research Agent Example.

This module demonstrates building a research agent using the deepagents package
with custom tools for web search and strategic thinking.
"""

from research_agent.prompts import (
    RESEARCHER_INSTRUCTIONS,
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
)
from research_agent.tools import (
    lightrag_get_status,
    lightrag_insert_text,
    lightrag_query,
    lightrag_upload_document,
    tavily_search,
    think_tool,
)

__all__ = [
    "tavily_search",
    "think_tool",
    "lightrag_query",
    "lightrag_insert_text",
    "lightrag_upload_document",
    "lightrag_get_status",
    "RESEARCHER_INSTRUCTIONS",
    "RESEARCH_WORKFLOW_INSTRUCTIONS",
    "SUBAGENT_DELEGATION_INSTRUCTIONS",
]
