#!/bin/bash

# Deep Research Agent - Development Environment Setup Script
# This script sets up the complete development environment from scratch

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEEP_RESEARCH_DIR="${SCRIPT_DIR}/deep_research"
DEEP_AGENTS_UI_DIR="${SCRIPT_DIR}/deep-agents-ui"
THREAD_SERVICE_DIR="${SCRIPT_DIR}/thread_service"

# Track what was set up for summary
SETUP_SUMMARY=()

echo -e "${BLUE}${BOLD}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     Deep Research Agent - Development Environment Setup       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# =============================================================================
# Helper Functions
# =============================================================================

print_step() {
    echo -e "\n${CYAN}${BOLD}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

ask_yes_no() {
    local prompt="$1"
    local default="${2:-y}"
    
    if [ "$default" = "y" ]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi
    
    echo -ne "${YELLOW}$prompt${NC}"
    read -r response
    response="${response:-$default}"
    
    case "$response" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

wait_for_postgres() {
    local max_attempts=30
    local attempt=1
    
    echo -ne "  Waiting for PostgreSQL to be ready"
    while [ $attempt -le $max_attempts ]; do
        if docker compose exec -T db pg_isready -U postgres &>/dev/null; then
            echo -e " ${GREEN}ready!${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    
    echo -e " ${RED}timeout${NC}"
    return 1
}

# =============================================================================
# Prerequisites Check
# =============================================================================

print_step "Checking Prerequisites"

# Check for uv
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version 2>/dev/null | head -1)
    print_success "uv is installed ($UV_VERSION)"
else
    print_warning "uv is not installed"
    if ask_yes_no "Would you like to install uv now?"; then
        print_info "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Source the updated PATH
        export PATH="$HOME/.local/bin:$PATH"
        if command -v uv &> /dev/null; then
            print_success "uv installed successfully"
            SETUP_SUMMARY+=("Installed uv package manager")
        else
            print_error "Failed to install uv. Please install manually and re-run this script."
            exit 1
        fi
    else
        print_error "uv is required. Please install it first:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
fi

# Check for Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version 2>/dev/null | head -1)
    print_success "Docker is installed ($DOCKER_VERSION)"
    DOCKER_AVAILABLE=true
else
    print_warning "Docker is not installed (required for PostgreSQL)"
    print_info "You can install Docker from: https://docs.docker.com/get-docker/"
    DOCKER_AVAILABLE=false
fi

# Check for docker compose
if [ "$DOCKER_AVAILABLE" = true ]; then
    if docker compose version &> /dev/null; then
        print_success "Docker Compose is available"
    else
        print_warning "Docker Compose is not available"
        DOCKER_AVAILABLE=false
    fi
fi

# Check for Node.js package manager
if command -v yarn &> /dev/null; then
    PKG_MANAGER="yarn"
    YARN_VERSION=$(yarn --version 2>/dev/null)
    print_success "yarn is installed (v$YARN_VERSION)"
elif command -v npm &> /dev/null; then
    PKG_MANAGER="npm"
    NPM_VERSION=$(npm --version 2>/dev/null)
    print_success "npm is installed (v$NPM_VERSION)"
else
    print_warning "Neither yarn nor npm is installed (required for UI)"
    print_info "You can install Node.js from: https://nodejs.org/"
    PKG_MANAGER=""
fi

# =============================================================================
# Environment Files Setup
# =============================================================================

print_step "Setting Up Environment Files"

# deep_research/.env
if [ -f "$DEEP_RESEARCH_DIR/.env" ]; then
    print_success "deep_research/.env already exists (skipping)"
else
    if [ -f "$DEEP_RESEARCH_DIR/.env.example" ]; then
        cp "$DEEP_RESEARCH_DIR/.env.example" "$DEEP_RESEARCH_DIR/.env"
        print_success "Created deep_research/.env from .env.example"
        SETUP_SUMMARY+=("Created deep_research/.env")
    else
        # Create .env.example first, then copy
        cat > "$DEEP_RESEARCH_DIR/.env.example" << 'EOF'
# API Keys for Deep Research Agent
# Fill in your actual API keys below

# Required for Claude model
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Required for Gemini model (get one at https://ai.google.dev/gemini-api/docs)
GOOGLE_API_KEY=your_google_api_key_here

# Required for web search (get one at https://www.tavily.com/)
TAVILY_API_KEY=your_tavily_api_key_here

# Optional: For LangSmith tracing (free to sign up at https://smith.langchain.com/settings)
LANGSMITH_API_KEY=your_langsmith_api_key_here

# Optional: For LightRAG knowledge base integration
LIGHTRAG_API_URL=https://lightrag-latest-xyu3.onrender.com
LIGHTRAG_API_KEY=your_lightrag_api_key_here
EOF
        cp "$DEEP_RESEARCH_DIR/.env.example" "$DEEP_RESEARCH_DIR/.env"
        print_success "Created deep_research/.env.example and .env"
        SETUP_SUMMARY+=("Created deep_research/.env")
    fi
fi

# thread_service/.env
if [ -f "$THREAD_SERVICE_DIR/.env" ]; then
    print_success "thread_service/.env already exists (skipping)"
else
    if [ -f "$THREAD_SERVICE_DIR/env.example" ]; then
        cp "$THREAD_SERVICE_DIR/env.example" "$THREAD_SERVICE_DIR/.env"
        print_success "Created thread_service/.env from env.example"
        SETUP_SUMMARY+=("Created thread_service/.env")
    else
        print_warning "thread_service/env.example not found"
    fi
fi

# deep-agents-ui/.env.local
if [ -f "$DEEP_AGENTS_UI_DIR/.env.local" ]; then
    print_success "deep-agents-ui/.env.local already exists (skipping)"
else
    cat > "$DEEP_AGENTS_UI_DIR/.env.local" << 'EOF'
# Deep Agents UI Environment Configuration

# Required: Generate with: openssl rand -base64 32
AUTH_SECRET=your_auth_secret_here

# LangGraph API endpoint (default: local development server)
NEXT_PUBLIC_LANGGRAPH_API_URL=http://localhost:8123

# Thread Service API endpoint (default: local development server)
NEXT_PUBLIC_THREAD_SERVICE_URL=http://localhost:8080

# Optional: OAuth providers (for social login)
# GOOGLE_CLIENT_ID=your_google_client_id
# GOOGLE_CLIENT_SECRET=your_google_client_secret
# GITHUB_CLIENT_ID=your_github_client_id
# GITHUB_CLIENT_SECRET=your_github_client_secret
EOF
    print_success "Created deep-agents-ui/.env.local"
    SETUP_SUMMARY+=("Created deep-agents-ui/.env.local")
fi

# =============================================================================
# Install Dependencies
# =============================================================================

print_step "Installing Dependencies"

# deep_research dependencies
print_info "Installing deep_research dependencies..."
cd "$DEEP_RESEARCH_DIR"
if uv sync 2>&1 | tail -3; then
    print_success "deep_research dependencies installed"
    SETUP_SUMMARY+=("Installed deep_research Python dependencies")
else
    print_error "Failed to install deep_research dependencies"
fi

# thread_service dependencies
print_info "Installing thread_service dependencies..."
cd "$THREAD_SERVICE_DIR"
if uv sync 2>&1 | tail -3; then
    print_success "thread_service dependencies installed"
    SETUP_SUMMARY+=("Installed thread_service Python dependencies")
else
    print_error "Failed to install thread_service dependencies"
fi

# deep-agents-ui dependencies
if [ -n "$PKG_MANAGER" ]; then
    print_info "Installing deep-agents-ui dependencies..."
    cd "$DEEP_AGENTS_UI_DIR"
    if [ "$PKG_MANAGER" = "yarn" ]; then
        if yarn install 2>&1 | tail -5; then
            print_success "deep-agents-ui dependencies installed"
            SETUP_SUMMARY+=("Installed deep-agents-ui Node dependencies")
        else
            print_error "Failed to install deep-agents-ui dependencies"
        fi
    else
        if npm install 2>&1 | tail -5; then
            print_success "deep-agents-ui dependencies installed"
            SETUP_SUMMARY+=("Installed deep-agents-ui Node dependencies")
        else
            print_error "Failed to install deep-agents-ui dependencies"
        fi
    fi
else
    print_warning "Skipping deep-agents-ui dependencies (no package manager available)"
fi

# =============================================================================
# Database Setup
# =============================================================================

print_step "Setting Up PostgreSQL Database"

if [ "$DOCKER_AVAILABLE" = true ]; then
    cd "$THREAD_SERVICE_DIR"
    
    # Check if container is already running
    if docker compose ps db 2>/dev/null | grep -q "running"; then
        print_success "PostgreSQL container is already running"
    else
        if ask_yes_no "Start PostgreSQL container with Docker Compose?"; then
            print_info "Starting PostgreSQL container..."
            if docker compose up -d db 2>&1 | tail -3; then
                print_success "PostgreSQL container started"
                SETUP_SUMMARY+=("Started PostgreSQL Docker container")
                
                # Wait for PostgreSQL to be ready
                if wait_for_postgres; then
                    # Run migrations
                    print_info "Running database migrations..."
                    if uv run alembic upgrade head 2>&1 | tail -5; then
                        print_success "Database migrations completed"
                        SETUP_SUMMARY+=("Applied database migrations")
                    else
                        print_error "Failed to run migrations"
                        print_info "You can run migrations manually: cd thread_service && uv run alembic upgrade head"
                    fi
                else
                    print_error "PostgreSQL failed to start in time"
                    print_info "Try: docker compose logs db"
                fi
            else
                print_error "Failed to start PostgreSQL container"
            fi
        else
            print_info "Skipping database setup"
        fi
    fi
else
    print_warning "Skipping database setup (Docker not available)"
    print_info "You can set up PostgreSQL manually or install Docker later"
fi

# =============================================================================
# Summary
# =============================================================================

cd "$SCRIPT_DIR"

echo -e "\n${BLUE}${BOLD}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                      Setup Complete!                          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

if [ ${#SETUP_SUMMARY[@]} -gt 0 ]; then
    echo -e "${GREEN}${BOLD}What was set up:${NC}"
    for item in "${SETUP_SUMMARY[@]}"; do
        echo -e "  ${GREEN}✓${NC} $item"
    done
    echo ""
fi

echo -e "${YELLOW}${BOLD}Next Steps:${NC}"
echo ""
echo -e "  ${BOLD}1. Configure API keys:${NC}"
echo -e "     ${CYAN}→${NC} Edit ${BOLD}deep_research/.env${NC} and add your API keys:"
echo "        - ANTHROPIC_API_KEY or GOOGLE_API_KEY (at least one required)"
echo "        - TAVILY_API_KEY (required for web search)"
echo ""
echo -e "  ${BOLD}2. Configure UI (optional):${NC}"
echo -e "     ${CYAN}→${NC} Edit ${BOLD}deep-agents-ui/.env.local${NC}:"
echo "        - Generate AUTH_SECRET: openssl rand -base64 32"
echo ""
echo -e "  ${BOLD}3. Run the development environment:${NC}"
echo -e "     ${CYAN}→${NC} Use the run script: ${BOLD}./run_dev.sh${NC}"
echo ""
echo -e "     Or start services individually:"
echo "        - Jupyter Notebook: cd deep_research && uv run jupyter notebook"
echo "        - LangGraph Server: cd deep_research && uv run langgraph dev"
echo "        - Thread Service:   cd thread_service && uv run python run.py"
echo "        - UI:               cd deep-agents-ui && yarn dev"
echo ""

if [ "$DOCKER_AVAILABLE" = true ]; then
    # Check if db is running
    cd "$THREAD_SERVICE_DIR"
    if docker compose ps db 2>/dev/null | grep -q "running"; then
        echo -e "${GREEN}${BOLD}Database Status:${NC} PostgreSQL is running on localhost:5432"
    else
        echo -e "${YELLOW}${BOLD}Database Status:${NC} PostgreSQL is not running"
        echo "  Start it with: cd thread_service && docker compose up -d db"
    fi
    cd "$SCRIPT_DIR"
fi

echo ""
echo -e "${BLUE}Happy coding! 🚀${NC}"

