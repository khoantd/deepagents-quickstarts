# Quick Start Guide

## Prerequisites

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Set up API keys**:
   - Copy `deep_research/.env.example` to `deep_research/.env`
   - Fill in your API keys:
     - `ANTHROPIC_API_KEY` - For Claude models
     - `GOOGLE_API_KEY` - For Gemini models  
     - `TAVILY_API_KEY` - For web search (required)
     - `LANGSMITH_API_KEY` - Optional, for tracing

## Running the Project

### Easy Way: Use the Dev Script

From the project root:

```bash
# Bash script (macOS/Linux)
./run_dev.sh

# Or Python script (cross-platform)
python run_dev.py
```

The script will:
1. Check prerequisites
2. Install dependencies
3. Verify API keys
4. Let you choose: Jupyter Notebook or LangGraph Server

### Manual Way

1. **Navigate to deep_research directory**:
   ```bash
   cd deep_research
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set environment variables** (or create `.env` file):
   ```bash
   export ANTHROPIC_API_KEY=your_key
   export GOOGLE_API_KEY=your_key
   export TAVILY_API_KEY=your_key
   ```

4. **Run in one of two modes**:

   **Jupyter Notebook** (interactive):
   ```bash
   uv run jupyter notebook research_agent.ipynb
   ```

   **LangGraph Server** (web interface):
   ```bash
   uv run langgraph dev
   ```

## What Each Mode Does

### Jupyter Notebook Mode
- Interactive development environment
- Step through the agent code cell by cell
- Great for understanding and experimenting
- See `research_agent.ipynb` for the notebook

### LangGraph Server Mode
- Web-based interface (opens in browser)
- Submit research queries directly
- View agent execution in real-time
- Can connect to [deepagents-ui](https://github.com/langchain-ai/deepagents-ui) for enhanced UI

## Troubleshooting

**"uv not found"**
- Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Restart your terminal

**"No API keys found"**
- Create `deep_research/.env` file with your keys
- Or export them in your shell: `export TAVILY_API_KEY=your_key`

**"Dependencies failed to install"**
- Make sure you're in the `deep_research` directory
- Try: `uv sync --refresh`

**Port already in use (LangGraph Server)**
- LangGraph uses port 8123 by default
- Kill the process using that port or change the port in `langgraph.json`

## Next Steps

- Read the [Deep Research README](deep_research/README.md) for detailed documentation
- Explore the code in `deep_research/research_agent/`
- Modify prompts in `research_agent/prompts.py`
- Add custom tools in `research_agent/tools.py`

