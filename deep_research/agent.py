"""Research Agent - Standalone script for LangGraph deployment.

This module creates a deep research agent with custom tools and prompts
for conducting web research with strategic thinking and context management.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

logger = logging.getLogger(__name__)

# Load .env file to ensure environment variables are available
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)

from research_agent.prompts import (
    CODE_ANALYST_INSTRUCTIONS,
    NEWS_RESEARCHER_INSTRUCTIONS,
    RESEARCHER_INSTRUCTIONS,
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
    TECHNICAL_DOCUMENTATION_INSTRUCTIONS,
    PROMPT_COMPOSER_INSTRUCTIONS,
)
from research_agent.tools import (
    lightrag_get_status,
    lightrag_insert_text,
    lightrag_query,
    lightrag_upload_document,
    tavily_search,
    think_tool,
)

# Limits
max_concurrent_research_units = 3
max_researcher_iterations = 3

# Get current date
current_date = datetime.now().strftime("%Y-%m-%d")

# Combine orchestrator instructions (RESEARCHER_INSTRUCTIONS only for sub-agents)
INSTRUCTIONS = (
    RESEARCH_WORKFLOW_INSTRUCTIONS
    + "\n\n"
    + "=" * 80
    + "\n\n"
    + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
        max_concurrent_research_units=max_concurrent_research_units,
        max_researcher_iterations=max_researcher_iterations,
    )
)

# Create research sub-agents
# Each sub-agent has: name, description, system_prompt, and tools

research_sub_agent = {
    "name": "research-agent",
    "description": "General research agent for comprehensive web research on any topic. Use for broad research questions, overviews, and general information gathering.",
    "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
    "tools": [
        tavily_search,
        think_tool,
        lightrag_query
    ],
}

news_researcher_agent = {
    "name": "news-researcher",
    "description": "News specialist for finding current events, recent developments, and breaking news. Use when the query requires up-to-date information from news sources.",
    "system_prompt": NEWS_RESEARCHER_INSTRUCTIONS.format(date=current_date),
    "tools": [
        tavily_search,
        think_tool
    ],
}

technical_docs_agent = {
    "name": "technical-docs-researcher",
    "description": "Technical documentation specialist for finding API docs, developer guides, and technical resources. Use for queries about APIs, libraries, frameworks, or technical implementation details.",
    "system_prompt": TECHNICAL_DOCUMENTATION_INSTRUCTIONS.format(date=current_date),
    "tools": [
        tavily_search,
        think_tool,
        lightrag_query
    ],
}

code_analyst_agent = {
    "name": "code-analyst",
    "description": "Code analysis specialist for analyzing codebases, understanding code patterns, and providing technical insights. Use for code review, architecture analysis, or understanding implementation patterns.",
    "system_prompt": CODE_ANALYST_INSTRUCTIONS.format(date=current_date),
    "tools": [
        tavily_search,
        think_tool
    ],
}

prompt_composer_agent = {
    "name": "prompt-composer",
    "description": "Specialist for composing, refining, and optimizing prompt templates and context prompts. Use when the user asks for help writing prompts or needs a template for a specific task.",
    "system_prompt": PROMPT_COMPOSER_INSTRUCTIONS.format(date=current_date),
    "tools": [
        tavily_search,
        think_tool,
        lightrag_query
    ],
}

# List of all sub-agents
_sub_agents_list = [
    research_sub_agent,
    news_researcher_agent,
    technical_docs_agent,
    code_analyst_agent,
    prompt_composer_agent,
]


def get_sub_agents():
    """Get list of available sub-agents with their metadata.
    
    Returns:
        List of dictionaries containing sub-agent information:
        - name: str
        - description: str
        - tools: list[str] (tool names)
    """
    result = []
    for sub_agent in _sub_agents_list:
        # Extract tool names from tool objects
        tool_names = []
        for tool in sub_agent.get("tools", []):
            # Try to get the name attribute from the tool
            tool_name = getattr(tool, "name", None)
            if tool_name is None:
                # Fallback: try to get name from __name__ or use string representation
                tool_name = getattr(tool, "__name__", str(tool))
            tool_names.append(tool_name)
        
        result.append({
            "name": sub_agent["name"],
            "description": sub_agent["description"],
            "tools": tool_names,
        })
    return result


# Model options:
# - OpenAI GPT-4o (recommended for best performance)
# - OpenAI GPT-4o-mini (faster and more cost-effective)
# - Claude 4.5: init_chat_model(model="anthropic:claude-sonnet-4-5-20250929", temperature=0.0)
# - LiteLLM Proxy: Set LITELLM_API_BASE environment variable to use LiteLLM proxy

# Check for LiteLLM proxy configuration
litellm_api_base = os.getenv("LITELLM_API_BASE")
litellm_api_key = os.getenv("LITELLM_API_KEY")
litellm_model = os.getenv("LITELLM_MODEL")

if litellm_api_base:
    # Use LiteLLM proxy
    # LiteLLM proxy exposes an OpenAI-compatible API
    # Set OPENAI_API_BASE to route through LiteLLM proxy
    base_url = litellm_api_base.rstrip("/")
    # Ensure it ends with /v1 for OpenAI-compatible endpoint
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    
    os.environ["OPENAI_API_BASE"] = base_url
    if litellm_api_key:
        os.environ["OPENAI_API_KEY"] = litellm_api_key
    
    # Determine model string for LiteLLM proxy
    # If LITELLM_MODEL is set, use it; otherwise default to gpt-4o
    # The model name should match what's configured in the LiteLLM proxy
    model_name = litellm_model or "gpt-4o"
    
    # Use OpenAI format since LiteLLM proxy is OpenAI-compatible
    model = init_chat_model(model=f"openai/{model_name}", temperature=0.0)
    logger.info(f"Initialized model via LiteLLM proxy: {model_name} at {base_url}")
else:
    # Use direct provider (backward compatibility)
    # Using OpenAI GPT-4o as default
    model = init_chat_model(model="openai:gpt-4o", temperature=0.0)
    logger.info("Initialized model via direct provider: openai:gpt-4o")

# Create the agent with multiple sub-agents
# Add or remove agents from this list to customize available sub-agents
agent = create_deep_agent(
    model=model,
    tools=[
        tavily_search,
        think_tool,
        lightrag_query,
        lightrag_insert_text,
        lightrag_upload_document,
        lightrag_get_status,
    ],
    system_prompt=INSTRUCTIONS,
    subagents=[
        research_sub_agent,  # General research
        news_researcher_agent,  # News and current events
        technical_docs_agent,  # Technical documentation
        code_analyst_agent,  # Code analysis
        prompt_composer_agent,  # Prompt composition
        # Add more agents here as needed
    ],
)
