#!/bin/bash

# Helper script to run LangGraph dev with environment variables from .env file
# This ensures all environment variables from .env are properly loaded

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

echo -e "${BLUE}🔧 LangGraph Dev${NC}\n"

# Load environment variables from .env if it exists
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}✓${NC} Found .env file, loading environment variables..."
    set -a
    # shellcheck disable=SC1090
    source <(grep -v '^#' "$ENV_FILE" | grep -v '^[[:space:]]*$' | sed 's/^/export /')
    set +a
    echo -e "${GREEN}✓${NC} Environment variables loaded\n"
else
    echo -e "${YELLOW}⚠️  No .env file found, using system environment variables${NC}\n"
fi

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

