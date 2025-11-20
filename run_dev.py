#!/usr/bin/env python3
"""Development run script for Deep Research Agent.

This script sets up and runs the research agent in development mode.
Supports:
- Jupyter Notebook (interactive development)
- LangGraph Server (web interface)
- Thread Service (authentication & persistence backend)
- Deep Agents UI (Next.js web application)
"""

import os
import sys
import subprocess
from pathlib import Path

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def print_colored(message: str, color: str = Colors.NC):
    """Print colored message."""
    print(f"{color}{message}{Colors.NC}")


def check_command(command: str) -> bool:
    """Check if a command is available."""
    try:
        subprocess.run(
            [command, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def create_env_example(env_path: Path):
    """Create .env.example file if it doesn't exist."""
    env_example = env_path / ".env.example"
    if env_example.exists():
        return
    
    env_example.write_text("""# API Keys for Deep Research Agent
# Copy this file to .env and fill in your actual API keys

# Required for Claude model
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Required for Gemini model (get one at https://ai.google.dev/gemini-api/docs)
GOOGLE_API_KEY=your_google_api_key_here

# Required for web search (get one at https://www.tavily.com/)
TAVILY_API_KEY=your_tavily_api_key_here

# Optional: For LangSmith tracing (free to sign up at https://smith.langchain.com/settings)
LANGSMITH_API_KEY=your_langsmith_api_key_here

# Optional: For LightRAG knowledge base integration
# LightRAG API URL (defaults to https://lightrag-latest-xyu3.onrender.com if not set)
LIGHTRAG_API_URL=https://lightrag-latest-xyu3.onrender.com
# LightRAG API Key (optional, for authentication)
LIGHTRAG_API_KEY=your_lightrag_api_key_here
""")


def check_env_vars() -> bool:
    """Check if required environment variables are set."""
    # At least one model key and Tavily key are required
    model_keys = ["ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    required_key = "TAVILY_API_KEY"
    
    has_model_key = any(os.getenv(key) for key in model_keys)
    has_tavily_key = bool(os.getenv(required_key))
    
    if has_tavily_key and has_model_key:
        print_colored("✓ Found required API keys in environment", Colors.GREEN)
        return True
    elif has_tavily_key:
        print_colored("⚠️  Found TAVILY_API_KEY but missing model API key", Colors.YELLOW)
        print_colored("   You need either ANTHROPIC_API_KEY or GOOGLE_API_KEY", Colors.YELLOW)
        return False
    return False


def main():
    """Main entry point."""
    print_colored("🚀 Deep Research Agent - Development Setup\n", Colors.BLUE)
    
    # Check if uv is installed
    if not check_command("uv"):
        print_colored("❌ Error: uv is not installed", Colors.RED)
        print_colored("Please install uv first:", Colors.YELLOW)
        print("curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)
    
    print_colored("✓ uv is installed", Colors.GREEN)
    
    # Get script directory and paths
    script_dir = Path(__file__).parent.resolve()
    deep_research_dir = script_dir / "deep_research"
    thread_service_dir = script_dir / "thread_service"
    deep_agents_ui_dir = script_dir / "deep-agents-ui"
    
    if not deep_research_dir.exists():
        print_colored("❌ Error: deep_research directory not found", Colors.RED)
        sys.exit(1)
    
    print_colored("✓ Changed to deep_research directory", Colors.GREEN)
    os.chdir(deep_research_dir)
    
    # Check for .env file
    env_file = deep_research_dir / ".env"
    if not env_file.exists():
        print_colored("⚠️  Warning: .env file not found", Colors.YELLOW)
        print_colored("Creating .env.example for reference...", Colors.YELLOW)
        create_env_example(deep_research_dir)
        print_colored("Please create a .env file with your API keys.", Colors.YELLOW)
        print_colored("You can copy .env.example to .env and fill in your keys.\n", Colors.YELLOW)
        
        if not check_env_vars():
            print_colored("❌ No API keys found in environment or .env file", Colors.RED)
            print_colored("Please set API keys in .env file or export them in your environment", Colors.YELLOW)
            sys.exit(1)
    else:
        print_colored("✓ Found .env file", Colors.GREEN)
        # Load .env file (simple parsing)
        try:
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    # Parse key=value pairs
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        # Only set if not already in environment (env vars take precedence)
                        if key and not os.getenv(key):
                            os.environ[key] = value
        except Exception as e:
            print_colored(f"⚠️  Warning: Could not parse .env file: {e}", Colors.YELLOW)
    
    # Install/update dependencies
    print_colored("\n📦 Installing dependencies...", Colors.BLUE)
    try:
        subprocess.run(["uv", "sync"], check=True)
        print_colored("✓ Dependencies installed", Colors.GREEN)
    except subprocess.CalledProcessError:
        print_colored("❌ Error: Failed to install dependencies", Colors.RED)
        sys.exit(1)
    
    # Ask user which mode to run
    print_colored("\nSelect run mode:", Colors.BLUE)
    print("1) Jupyter Notebook (interactive development)")
    print("2) LangGraph Server (web interface)")
    print("3) Thread Service (authentication & persistence backend)")
    print("4) Deep Agents UI (Next.js web application)")
    print("5) Exit")
    
    try:
        choice = input(f"{Colors.YELLOW}Enter choice [1-5]: {Colors.NC}").strip()
    except KeyboardInterrupt:
        print_colored("\n\nExiting...", Colors.BLUE)
        sys.exit(0)
    
    if choice == "1":
        print_colored("\n📓 Starting Jupyter Notebook...", Colors.GREEN)
        print_colored("The notebook will open in your browser\n", Colors.BLUE)
        try:
            subprocess.run(["uv", "run", "jupyter", "notebook", "research_agent.ipynb"], check=True)
        except KeyboardInterrupt:
            print_colored("\n\nStopped Jupyter Notebook", Colors.YELLOW)
        except subprocess.CalledProcessError:
            print_colored("❌ Error: Failed to start Jupyter Notebook", Colors.RED)
            sys.exit(1)
    
    elif choice == "2":
        print_colored("\n🌐 Starting LangGraph Server...", Colors.GREEN)
        print_colored("The server will start and open in your browser", Colors.BLUE)
        print_colored("Press Ctrl+C to stop the server\n", Colors.YELLOW)
        try:
            subprocess.run(["uv", "run", "langgraph", "dev"], check=True)
        except KeyboardInterrupt:
            print_colored("\n\nStopped LangGraph Server", Colors.YELLOW)
        except subprocess.CalledProcessError:
            print_colored("❌ Error: Failed to start LangGraph Server", Colors.RED)
            sys.exit(1)
    
    elif choice == "3":
        if not thread_service_dir.exists():
            print_colored("❌ Error: thread_service directory not found", Colors.RED)
            sys.exit(1)
        
        print_colored("\n🔧 Starting Thread Service...", Colors.GREEN)
        print_colored("The service provides authentication and thread persistence", Colors.BLUE)
        print_colored("HTTP API: http://localhost:8080", Colors.BLUE)
        print_colored("gRPC: localhost:50051", Colors.BLUE)
        print_colored("Press Ctrl+C to stop the service\n", Colors.YELLOW)
        
        # Change to thread_service directory
        os.chdir(thread_service_dir)
        
        # Check if .env exists in thread_service
        thread_env_file = thread_service_dir / ".env"
        if not thread_env_file.exists():
            print_colored("⚠️  Warning: .env file not found in thread_service", Colors.YELLOW)
            print_colored("   Using default configuration. Create .env for custom settings.", Colors.YELLOW)
        
        # Install dependencies for thread_service
        print_colored("📦 Installing thread_service dependencies...", Colors.BLUE)
        try:
            subprocess.run(["uv", "sync"], check=True, cwd=thread_service_dir)
            print_colored("✓ Dependencies installed", Colors.GREEN)
        except subprocess.CalledProcessError:
            print_colored("❌ Error: Failed to install thread_service dependencies", Colors.RED)
            sys.exit(1)
        
        # Run the thread service
        try:
            subprocess.run(["uv", "run", "python", "run.py"], check=True, cwd=thread_service_dir)
        except KeyboardInterrupt:
            print_colored("\n\nStopped Thread Service", Colors.YELLOW)
        except subprocess.CalledProcessError:
            print_colored("❌ Error: Failed to start Thread Service", Colors.RED)
            sys.exit(1)
    
    elif choice == "4":
        if not deep_agents_ui_dir.exists():
            print_colored("❌ Error: deep-agents-ui directory not found", Colors.RED)
            sys.exit(1)
        
        # Check for package manager (yarn or npm)
        pkg_manager = None
        if check_command("yarn"):
            pkg_manager = "yarn"
            print_colored("✓ yarn is available", Colors.GREEN)
        elif check_command("npm"):
            pkg_manager = "npm"
            print_colored("✓ npm is available", Colors.GREEN)
        else:
            print_colored("❌ Error: Neither yarn nor npm is installed", Colors.RED)
            print_colored("   Please install yarn or npm to run the UI", Colors.YELLOW)
            sys.exit(1)
        
        print_colored("\n🌐 Starting Deep Agents UI...", Colors.GREEN)
        print_colored("The Next.js app will start on http://localhost:3000", Colors.BLUE)
        print_colored("Press Ctrl+C to stop the server\n", Colors.YELLOW)
        
        # Change to deep-agents-ui directory
        os.chdir(deep_agents_ui_dir)
        
        # Check if node_modules exists, if not install dependencies
        node_modules = deep_agents_ui_dir / "node_modules"
        if not node_modules.exists():
            print_colored("📦 Installing dependencies...", Colors.BLUE)
            try:
                if pkg_manager == "yarn":
                    subprocess.run(["yarn", "install"], check=True, cwd=deep_agents_ui_dir)
                else:
                    subprocess.run(["npm", "install"], check=True, cwd=deep_agents_ui_dir)
                print_colored("✓ Dependencies installed", Colors.GREEN)
            except subprocess.CalledProcessError:
                print_colored("❌ Error: Failed to install dependencies", Colors.RED)
                sys.exit(1)
        else:
            print_colored("✓ Dependencies already installed", Colors.GREEN)
        
        # Check for .env.local file
        env_local_file = deep_agents_ui_dir / ".env.local"
        if not env_local_file.exists():
            print_colored("⚠️  Warning: .env.local file not found", Colors.YELLOW)
            print_colored("   Create .env.local with AUTH_SECRET and OAuth credentials if needed", Colors.YELLOW)
        
        # Run the development server
        try:
            if pkg_manager == "yarn":
                subprocess.run(["yarn", "dev"], check=True, cwd=deep_agents_ui_dir)
            else:
                subprocess.run(["npm", "run", "dev"], check=True, cwd=deep_agents_ui_dir)
        except KeyboardInterrupt:
            print_colored("\n\nStopped Deep Agents UI", Colors.YELLOW)
        except subprocess.CalledProcessError:
            print_colored("❌ Error: Failed to start Deep Agents UI", Colors.RED)
            sys.exit(1)
    
    elif choice == "5":
        print_colored("Exiting...", Colors.BLUE)
        sys.exit(0)
    
    else:
        print_colored("Invalid choice. Exiting...", Colors.RED)
        sys.exit(1)


if __name__ == "__main__":
    main()

