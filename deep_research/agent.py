"""Research Agent - Standalone script for LangGraph deployment.

This module creates a deep research agent with custom tools and prompts
for conducting web research with strategic thinking and context management.
"""

from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

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
)
from research_agent.tools import tavily_search, think_tool

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
    "tools": [tavily_search, think_tool],
}

news_researcher_agent = {
    "name": "news-researcher",
    "description": "News specialist for finding current events, recent developments, and breaking news. Use when the query requires up-to-date information from news sources.",
    "system_prompt": NEWS_RESEARCHER_INSTRUCTIONS.format(date=current_date),
    "tools": [tavily_search, think_tool],
}

technical_docs_agent = {
    "name": "technical-docs-researcher",
    "description": "Technical documentation specialist for finding API docs, developer guides, and technical resources. Use for queries about APIs, libraries, frameworks, or technical implementation details.",
    "system_prompt": TECHNICAL_DOCUMENTATION_INSTRUCTIONS.format(date=current_date),
    "tools": [tavily_search, think_tool],
}

code_analyst_agent = {
    "name": "code-analyst",
    "description": "Code analysis specialist for analyzing codebases, understanding code patterns, and providing technical insights. Use for code review, architecture analysis, or understanding implementation patterns.",
    "system_prompt": CODE_ANALYST_INSTRUCTIONS.format(date=current_date),
    "tools": [tavily_search, think_tool],
}

# Model options:
# - OpenAI GPT-4o (recommended for best performance)
# - OpenAI GPT-4o-mini (faster and more cost-effective)
# - Claude 4.5: init_chat_model(model="anthropic:claude-sonnet-4-5-20250929", temperature=0.0)

# Using OpenAI GPT-4o
model = init_chat_model(model="openai:gpt-4o", temperature=0.0)

# Create the agent with multiple sub-agents
# Add or remove agents from this list to customize available sub-agents
agent = create_deep_agent(
    model=model,
    tools=[tavily_search, think_tool],
    system_prompt=INSTRUCTIONS,
    subagents=[
        research_sub_agent,  # General research
        news_researcher_agent,  # News and current events
        technical_docs_agent,  # Technical documentation
        code_analyst_agent,  # Code analysis
        # Add more agents here as needed
    ],
)
