# 🚀 Deep Research

## 🚀 Quickstart

**Prerequisites**: Install [uv](https://docs.astral.sh/uv/) package manager:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Ensure you are in the `deep_research` directory:
```bash
cd deep_research
```

Install packages:
```bash
uv sync
```

Set your API keys in your environment:

```bash
export ANTHROPIC_API_KEY=your_anthropic_api_key_here  # Required for Claude model
export GOOGLE_API_KEY=your_google_api_key_here        # Required for Gemini model ([get one here](https://ai.google.dev/gemini-api/docs))
export TAVILY_API_KEY=your_tavily_api_key_here        # Required for web search ([get one here](https://www.tavily.com/)) with a generous free tier

# Optional: LightRAG knowledge base integration
export LIGHTRAG_API_URL=https://lightrag-latest-xyu3.onrender.com  # LightRAG API URL (defaults to this if not set)
export LIGHTRAG_API_KEY=your_lightrag_api_key_here     # Optional: API key for LightRAG authentication
```

## Usage Options

You can run this quickstart in two ways:

### Option 1: Jupyter Notebook

Run the interactive notebook to step through the research agent:

```bash
uv run jupyter notebook research_agent.ipynb
```

### Option 2: LangGraph Server

Run a local [LangGraph server](https://langchain-ai.github.io/langgraph/tutorials/langgraph-platform/local-server/) with a web interface:

**Recommended**: Use the helper script to ensure environment variables from .env are properly loaded:

```bash
# Bash (macOS/Linux)
./run_langgraph.sh

# Python (cross-platform)
python run_langgraph.py
```

**Or manually**:

```bash
langgraph dev
```

LangGraph server will open a new browser window with the Studio interface, which you can submit your search query to: 

<img width="2869" height="1512" alt="Screenshot 2025-11-17 at 11 42 59 AM" src="https://github.com/user-attachments/assets/03090057-c199-42fe-a0f7-769704c2124b" />

You can also connect the LangGraph server to a [UI specifically designed for deepagents](https://github.com/langchain-ai/deep-agents-ui):

```bash
$ git clone https://github.com/langchain-ai/deepagents-ui.git
$ cd deepagents-ui
$ yarn install
$ yarn dev
```

Then follow the instructions in the [deepagents-ui README](https://github.com/langchain-ai/deepagents-ui?tab=readme-ov-file#connecting-to-a-langgraph-server) to connect the UI to the running LangGraph server.

This provides a user-friendly chat interface and visualization of files in state.

## 📚 Resources

- **[Deep Research Course](https://academy.langchain.com/courses/deep-research-with-langgraph)** - Full course on deep research with LangGraph

### Custom Model

By default, `deepagents` uses `"claude-sonnet-4-5-20250929"`. You can customize this by passing any [LangChain model object](https://python.langchain.com/docs/integrations/chat/). See the Deepagents package [README](https://github.com/langchain-ai/deepagents?tab=readme-ov-file#model) for more details.

```python
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

# Using Claude
model = init_chat_model(model="anthropic:claude-sonnet-4-5-20250929", temperature=0.0)

# Using Gemini
from langchain_google_genai import ChatGoogleGenerativeAI
model = ChatGoogleGenerativeAI(model="gemini-3-pro-preview")

agent = create_deep_agent(
    model=model,
)
```

### Custom Instructions

The deep research agent uses custom instructions defined in `deep_research/research_agent/prompts.py` that complement (rather than duplicate) the default middleware instructions. You can modify these in any way you want. 

| Instruction Set | Purpose |
|----------------|---------|
| `RESEARCH_WORKFLOW_INSTRUCTIONS` | Defines the 5-step research workflow: save request → plan with TODOs → delegate to sub-agents → synthesize → respond. Includes research-specific planning guidelines like batching similar tasks and scaling rules for different query types. |
| `SUBAGENT_DELEGATION_INSTRUCTIONS` | Provides concrete delegation strategies with examples: simple queries use 1 sub-agent, comparisons use 1 per element, multi-faceted research uses 1 per aspect. Sets limits on parallel execution (max 3 concurrent) and iteration rounds (max 3). |
| `RESEARCHER_INSTRUCTIONS` | Guides individual research sub-agents to conduct focused web searches. Includes hard limits (2-3 searches for simple queries, max 5 for complex), emphasizes using `think_tool` after each search for strategic reflection, and defines stopping criteria. |

### Custom Tools

The deep research agent adds the following custom tools beyond the built-in deepagent tools. You can also use your own tools, including via MCP servers. See the Deepagents package [README](https://github.com/langchain-ai/deepagents?tab=readme-ov-file#mcp) for more details.

| Tool Name | Description |
|-----------|-------------|
| `tavily_search` | Web search tool that uses Tavily purely as a URL discovery engine. Performs searches using Tavily API to find relevant URLs, fetches full webpage content via HTTP with proper User-Agent headers (avoiding 403 errors), converts HTML to markdown, and returns the complete content without summarization to preserve all information for the agent's analysis. Works with both Claude and Gemini models. |
| `think_tool` | Strategic reflection mechanism that helps the agent pause and assess progress between searches, analyze findings, identify gaps, and plan next steps. |
| `lightrag_query` | Query the LightRAG knowledge base for stored information. Use this to retrieve information from documents that have been previously uploaded or text that has been inserted into the system. Supports multiple query modes: 'mix' (default), 'local' (entity-based), 'global' (relationship-based), 'hybrid', 'naive', or 'bypass'. |
| `lightrag_insert_text` | Insert text into the LightRAG knowledge base for later retrieval. Use this to store research findings, summaries, or important information so it can be retrieved later using `lightrag_query`. |
| `lightrag_upload_document` | Upload a file to the LightRAG knowledge base for indexing. The document will be processed and indexed for later retrieval. Supports various file formats (PDF, text files, etc.). |
| `lightrag_get_status` | Get the status of documents and pipeline in the LightRAG knowledge base. Check document processing status (pending, processing, processed, failed) and pipeline status (busy, progress, current job). |

#### When to Use LightRAG vs Web Search

- **Use `tavily_search`** when you need:
  - Current, up-to-date information from the web
  - Information that changes frequently (news, recent events)
  - Broad exploration of topics not in your knowledge base
  - Finding new sources and URLs

- **Use `lightrag_query`** when you need:
  - Information from documents you've previously uploaded
  - Querying a curated knowledge base
  - Retrieving stored research findings
  - Information that has been inserted into the system

The agent can use both tools together - for example, using web search to find new information and then storing key findings in LightRAG for future retrieval.

> **Note**: LightRAG tools are optional. If `LIGHTRAG_API_URL` and `LIGHTRAG_API_KEY` are not configured, the tools will return an error message but won't break the agent. The agent will continue to work with web search functionality.

