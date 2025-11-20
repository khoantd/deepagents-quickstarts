#!/bin/bash

# Deep Research Agent - Development Run Script
# This script sets up and runs the research agent in development mode

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEEP_RESEARCH_DIR="${SCRIPT_DIR}/deep_research"
DEEP_AGENTS_UI_DIR="${SCRIPT_DIR}/deep-agents-ui"
THREAD_SERVICE_DIR="${SCRIPT_DIR}/thread_service"

echo -e "${BLUE}🚀 Deep Research Agent - Development Setup${NC}\n"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ Error: uv is not installed${NC}"
    echo -e "${YELLOW}Please install uv first:${NC}"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo -e "${GREEN}✓${NC} uv is installed"

# Check if npm or yarn is installed (for UI)
if command -v yarn &> /dev/null; then
    PKG_MANAGER="yarn"
    echo -e "${GREEN}✓${NC} yarn is installed"
elif command -v npm &> /dev/null; then
    PKG_MANAGER="npm"
    echo -e "${GREEN}✓${NC} npm is installed"
else
    echo -e "${YELLOW}⚠️  Warning: neither npm nor yarn is installed. UI mode will not work.${NC}"
fi

# Change to deep_research directory
if [ ! -d "$DEEP_RESEARCH_DIR" ]; then
    echo -e "${RED}❌ Error: deep_research directory not found${NC}"
    exit 1
fi

cd "$DEEP_RESEARCH_DIR"
echo -e "${GREEN}✓${NC} Changed to deep_research directory"

# Check for .env file
ENV_FILE="${DEEP_RESEARCH_DIR}/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    echo -e "${YELLOW}Creating .env.example for reference...${NC}"
    
    cat > "${DEEP_RESEARCH_DIR}/.env.example" << 'EOF'
# API Keys for Deep Research Agent
# Copy this file to .env and fill in your actual API keys

# Required for Claude model
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Required for Gemini model (get one at https://ai.google.dev/gemini-api/docs)
GOOGLE_API_KEY=your_google_api_key_here

# Required for web search (get one at https://www.tavily.com/)
TAVILY_API_KEY=your_tavily_api_key_here

# Optional: For LangSmith tracing (free to sign up at https://smith.langchain.com/settings)
LANGSMITH_API_KEY=your_langsmith_api_key_here
EOF
    
    echo -e "${YELLOW}Please create a .env file with your API keys.${NC}"
    echo -e "${YELLOW}You can copy .env.example to .env and fill in your keys.${NC}\n"
    
    # Check if at least one key is set in environment
    if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ] && [ -z "$TAVILY_API_KEY" ]; then
        echo -e "${RED}❌ No API keys found in environment or .env file${NC}"
        echo -e "${YELLOW}Please set API keys in .env file or export them in your environment${NC}"
        exit 1
    else
        echo -e "${GREEN}✓${NC} Found API keys in environment variables"
    fi
else
    echo -e "${GREEN}✓${NC} Found .env file"
    # Load .env file (filter out comments and empty lines)
    export $(cat "$ENV_FILE" | grep -v '^#' | grep -v '^[[:space:]]*$' | xargs)
fi

# Install/update dependencies
echo -e "\n${BLUE}📦 Installing dependencies...${NC}"
uv sync
echo -e "${GREEN}✓${NC} Dependencies installed"

# Check if langgraph is available (for server mode)
if ! uv run langgraph --version &> /dev/null; then
    echo -e "${YELLOW}⚠️  Warning: langgraph CLI not found, server mode may not work${NC}"
fi

# Ask user which mode to run
echo -e "\n${BLUE}Select run mode:${NC}"
echo "1) Jupyter Notebook (interactive development)"
echo "2) LangGraph Server (web interface)"
echo "3) Thread Service (authentication & persistence backend)"
echo "4) Deep Agents UI (Next.js web application)"
echo "5) Exit"
echo -ne "${YELLOW}Enter choice [1-5]: ${NC}"
read -r choice

case $choice in
    1)
        echo -e "\n${GREEN}📓 Starting Jupyter Notebook...${NC}"
        echo -e "${BLUE}The notebook will open in your browser${NC}\n"
        uv run jupyter notebook research_agent.ipynb
        ;;
    2)
        echo -e "\n${GREEN}🌐 Starting LangGraph Server...${NC}"
        echo -e "${BLUE}The server will start and open in your browser${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}\n"
        uv run langgraph dev
        ;;
    3)
        if [ ! -d "$THREAD_SERVICE_DIR" ]; then
            echo -e "${RED}❌ Error: thread_service directory not found${NC}"
            exit 1
        fi
        
        echo -e "\n${GREEN}🔧 Starting Thread Service...${NC}"
        echo -e "${BLUE}The service provides authentication and thread persistence${NC}"
        echo -e "${BLUE}HTTP API: http://localhost:8080${NC}"
        echo -e "${BLUE}gRPC: localhost:50051${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop the service${NC}\n"
        
        cd "$THREAD_SERVICE_DIR"
        
        # Check if .env exists in thread_service
        if [ ! -f "$THREAD_SERVICE_DIR/.env" ]; then
            echo -e "${YELLOW}⚠️  Warning: .env file not found in thread_service${NC}"
            echo -e "${YELLOW}   Using default configuration. Create .env for custom settings.${NC}"
        fi
        
        # Install dependencies for thread_service
        echo -e "${BLUE}📦 Installing thread_service dependencies...${NC}"
        uv sync
        
        # Run the thread service
        uv run python run.py
        ;;
    4)
        if [ -z "$PKG_MANAGER" ]; then
            echo -e "${RED}❌ Error: npm or yarn is required for UI mode${NC}"
            exit 1
        fi
        
        if [ ! -d "$DEEP_AGENTS_UI_DIR" ]; then
            echo -e "${RED}❌ Error: deep-agents-ui directory not found${NC}"
            exit 1
        fi

        echo -e "\n${GREEN}🌐 Starting Deep Agents UI...${NC}"
        echo -e "${BLUE}The Next.js app will start on http://localhost:3000${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}\n"
        
        cd "$DEEP_AGENTS_UI_DIR"
        
        # Check if node_modules exists, if not install dependencies
        if [ ! -d "$DEEP_AGENTS_UI_DIR/node_modules" ]; then
            echo -e "${BLUE}📦 Installing dependencies...${NC}"
            $PKG_MANAGER install
            echo -e "${GREEN}✓${NC} Dependencies installed"
        else
            echo -e "${GREEN}✓${NC} Dependencies already installed"
        fi
        
        # Check for .env.local file
        if [ ! -f "$DEEP_AGENTS_UI_DIR/.env.local" ]; then
            echo -e "${YELLOW}⚠️  Warning: .env.local file not found${NC}"
            echo -e "${YELLOW}   Create .env.local with AUTH_SECRET and OAuth credentials if needed${NC}"
        fi
        
        echo -e "${BLUE}Starting development server...${NC}"
        $PKG_MANAGER run dev
        ;;
    5)
        echo -e "${BLUE}Exiting...${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice. Exiting...${NC}"
        exit 1
        ;;
esac

