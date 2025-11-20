#!/usr/bin/env python3
"""Helper script to run LangGraph dev with proper LangSmith environment variables.

This ensures LANGSMITH_API_KEY and LANGSMITH_WORKSPACE_ID are properly exported
before running langgraph dev.
"""

import os
import subprocess
import sys
from pathlib import Path


def load_env_file(env_path: Path) -> dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    
    if not env_path.exists():
        return env_vars
    
    with open(env_path, encoding="utf-8") as f:
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
                
                env_vars[key] = value
    
    return env_vars


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    env_file = script_dir / ".env"
    
    print("🔧 LangGraph Dev with LangSmith Configuration\n")
    
    # Check if .env file exists
    if not env_file.exists():
        print(f"❌ Error: .env file not found at {env_file}")
        sys.exit(1)
    
    print("✓ Found .env file")
    
    # Load environment variables
    env_vars = load_env_file(env_file)
    
    # Set up environment
    for key, value in env_vars.items():
        # Only set if not already in environment (env vars take precedence)
        if key and not os.getenv(key):
            os.environ[key] = value
    
    # Verify LangSmith variables
    langsmith_key = os.getenv("LANGSMITH_API_KEY")
    workspace_id = os.getenv("LANGSMITH_WORKSPACE_ID")
    
    if not langsmith_key:
        print("⚠️  Warning: LANGSMITH_API_KEY not found in .env file")
        print("LangSmith tracing will be disabled\n")
    else:
        masked_key = langsmith_key[:10] + "..." + langsmith_key[-4:] if len(langsmith_key) > 14 else "***"
        print(f"✓ LANGSMITH_API_KEY loaded: {masked_key}")
        
        if not workspace_id:
            print("⚠️  Warning: LANGSMITH_WORKSPACE_ID not found in .env file")
            print("If your API key is org-scoped, this may cause 403 errors\n")
        else:
            print(f"✓ LANGSMITH_WORKSPACE_ID loaded: {workspace_id}\n")
        
        # Also set LANGCHAIN_API_KEY as alias (some versions use this)
        if not os.getenv("LANGCHAIN_API_KEY"):
            os.environ["LANGCHAIN_API_KEY"] = langsmith_key
            print("✓ LANGCHAIN_API_KEY set as alias\n")
    
    # Change to script directory
    os.chdir(script_dir)
    
    # Check if uv is available
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: uv is not installed")
        sys.exit(1)
    
    # Run langgraph dev
    print("🚀 Starting LangGraph Server...")
    print("Press Ctrl+C to stop the server\n")
    
    try:
        subprocess.run(["uv", "run", "langgraph", "dev"], check=True)
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running langgraph dev: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

