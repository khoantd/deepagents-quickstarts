#!/usr/bin/env python3
"""Helper script to run LangGraph dev with environment variables from .env file.

This ensures all environment variables from .env are properly loaded
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
    
    print("🔧 LangGraph Dev\n")
    
    # Load environment variables from .env if it exists
    if env_file.exists():
        print("✓ Found .env file, loading environment variables...")
        env_vars = load_env_file(env_file)
        
        # Set up environment
        for key, value in env_vars.items():
            # Only set if not already in environment (env vars take precedence)
            if key and not os.getenv(key):
                os.environ[key] = value
        print("✓ Environment variables loaded\n")
    else:
        print("⚠️  No .env file found, using system environment variables\n")
    
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
    
    # Pass the current environment (with all variables) to subprocess
    env = os.environ.copy()
    
    try:
        subprocess.run(["uv", "run", "langgraph", "dev"], check=True, env=env)
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running langgraph dev: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

