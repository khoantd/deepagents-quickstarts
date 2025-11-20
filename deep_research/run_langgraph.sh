#!/bin/bash

# Helper script to run LangGraph dev with proper LangSmith environment variables
# This ensures LANGSMITH_API_KEY and LANGSMITH_WORKSPACE_ID are properly exported

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

echo -e "${BLUE}🔧 LangGraph Dev with LangSmith Configuration${NC}\n"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Error: .env file not found at ${ENV_FILE}${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found .env file"

# Load and export LangSmith variables from .env
LANGSMITH_API_KEY=""
LANGSMITH_WORKSPACE_ID=""

while IFS= read -r line || [ -n "$line" ]; do
    # Skip comments and empty lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    
    # Parse key=value pairs
    if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
        key="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        
        # Remove quotes if present
        value="${value#\"}"
        value="${value%\"}"
        value="${value#\'}"
        value="${value%\'}"
        
        # Remove leading/trailing whitespace
        key="${key%"${key##*[![:space:]]}"}"
        key="${key#"${key%%[![:space:]]*}"}"
        value="${value%"${value##*[![:space:]]}"}"
        value="${value#"${value%%[![:space:]]*}"}"
        
        case "$key" in
            LANGSMITH_API_KEY)
                LANGSMITH_API_KEY="$value"
                ;;
            LANGSMITH_WORKSPACE_ID)
                LANGSMITH_WORKSPACE_ID="$value"
                ;;
        esac
    fi
done < "$ENV_FILE"

# Verify LangSmith variables are set
if [ -z "$LANGSMITH_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  Warning: LANGSMITH_API_KEY not found in .env file${NC}"
    echo -e "${YELLOW}LangSmith tracing will be disabled${NC}\n"
else
    export LANGSMITH_API_KEY
    masked_key="${LANGSMITH_API_KEY:0:10}...${LANGSMITH_API_KEY: -4}"
    echo -e "${GREEN}✓${NC} LANGSMITH_API_KEY loaded: ${masked_key}"
    
    if [ -z "$LANGSMITH_WORKSPACE_ID" ]; then
        echo -e "${YELLOW}⚠️  Warning: LANGSMITH_WORKSPACE_ID not found in .env file${NC}"
        echo -e "${YELLOW}If your API key is org-scoped, this may cause 403 errors${NC}\n"
    else
        export LANGSMITH_WORKSPACE_ID
        echo -e "${GREEN}✓${NC} LANGSMITH_WORKSPACE_ID loaded: ${LANGSMITH_WORKSPACE_ID}\n"
    fi
    
    # Also set LANGCHAIN_API_KEY as alias (some versions use this)
    export LANGCHAIN_API_KEY="$LANGSMITH_API_KEY"
    echo -e "${GREEN}✓${NC} LANGCHAIN_API_KEY set as alias\n"
fi

# Load all other environment variables from .env
echo -e "${BLUE}Loading other environment variables from .env...${NC}"
set -a
# shellcheck disable=SC1090
source <(grep -v '^#' "$ENV_FILE" | grep -v '^[[:space:]]*$' | sed 's/^/export /')
set +a
echo -e "${GREEN}✓${NC} Environment variables loaded\n"

# Change to script directory
cd "$SCRIPT_DIR"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ Error: uv is not installed${NC}"
    exit 1
fi

# Run langgraph dev
echo -e "${BLUE}🚀 Starting LangGraph Server...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}\n"

uv run langgraph dev

