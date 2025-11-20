"""Diagnostic script to check LangSmith configuration.

This script helps identify issues with LangSmith API key and workspace ID setup.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"✓ Loaded .env file from: {env_path}")
else:
    print(f"⚠️  .env file not found at: {env_path}")

print("\n" + "=" * 80)
print("LangSmith Configuration Check")
print("=" * 80 + "\n")

# Check LANGSMITH_API_KEY
langsmith_key = os.getenv("LANGSMITH_API_KEY")
if langsmith_key:
    # Mask the key for security
    masked_key = langsmith_key[:10] + "..." + langsmith_key[-4:] if len(langsmith_key) > 14 else "***"
    print(f"✓ LANGSMITH_API_KEY is set: {masked_key}")
    print(f"  Full length: {len(langsmith_key)} characters")
    
    # Check for common issues
    if langsmith_key.strip() != langsmith_key:
        print("  ⚠️  WARNING: Key has leading/trailing whitespace!")
    if not langsmith_key.startswith("lsv2_"):
        print("  ⚠️  WARNING: Key doesn't start with 'lsv2_' - might be invalid format")
else:
    print("❌ LANGSMITH_API_KEY is NOT set")

# Check LANGSMITH_WORKSPACE_ID
workspace_id = os.getenv("LANGSMITH_WORKSPACE_ID")
if workspace_id:
    print(f"✓ LANGSMITH_WORKSPACE_ID is set: {workspace_id}")
    
    # Check for common issues
    if workspace_id.strip() != workspace_id:
        print("  ⚠️  WARNING: Workspace ID has leading/trailing whitespace!")
    if len(workspace_id) < 10:
        print("  ⚠️  WARNING: Workspace ID seems too short")
else:
    print("❌ LANGSMITH_WORKSPACE_ID is NOT set")
    print("  ⚠️  If your API key is org-scoped, this is REQUIRED!")

# Check LANGCHAIN_API_KEY (some versions use this as alias)
langchain_key = os.getenv("LANGCHAIN_API_KEY")
if langchain_key:
    print(f"\n⚠️  LANGCHAIN_API_KEY is also set (might override LANGSMITH_API_KEY)")
    masked_key = langchain_key[:10] + "..." + langchain_key[-4:] if len(langchain_key) > 14 else "***"
    print(f"  Value: {masked_key}")

# Check LANGCHAIN_TRACING_V2
tracing_v2 = os.getenv("LANGCHAIN_TRACING_V2")
if tracing_v2:
    print(f"\nLANGCHAIN_TRACING_V2 is set: {tracing_v2}")
    if tracing_v2.lower() == "false":
        print("  ℹ️  Tracing is disabled - LangSmith won't be used")

# Check LANGSMITH_ENDPOINT (for regional instances)
endpoint = os.getenv("LANGSMITH_ENDPOINT")
if endpoint:
    print(f"\nLANGSMITH_ENDPOINT is set: {endpoint}")
else:
    print(f"\nLANGSMITH_ENDPOINT not set (using default: https://api.smith.langchain.com)")

print("\n" + "=" * 80)
print("Recommendations:")
print("=" * 80)

if not langsmith_key:
    print("1. Set LANGSMITH_API_KEY in your .env file")
    print("   Get one at: https://smith.langchain.com/settings")
elif not workspace_id:
    print("1. Set LANGSMITH_WORKSPACE_ID in your .env file")
    print("   Find it in: https://smith.langchain.com/settings")
    print("   (Required if your API key is org-scoped)")
else:
    print("1. ✓ Both API key and workspace ID are set")
    print("2. Verify the API key is valid and not expired:")
    print("   - Visit https://smith.langchain.com/settings")
    print("   - Check that the key matches and is active")
    print("3. Verify the workspace ID matches your API key:")
    print("   - The workspace ID should match the workspace associated with your key")
    print("4. If using org-scoped key, ensure workspace ID is correct for that org")

print("\n" + "=" * 80)
print("Testing API Connectivity...")
print("=" * 80)

try:
    from langsmith import Client
    import requests
    
    client = Client()
    try:
        # Try to list projects (read-only operation usually)
        projects = list(client.list_projects(limit=1))
        print("✓ Connection successful! API Key and Workspace ID are valid.")
        print(f"  Accessing Workspace: {workspace_id if workspace_id else 'Default'}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("❌ Connection FAILED: 403 Forbidden")
            print("  ROOT CAUSE: The API Key does not have permission to access the specified Workspace.")
            print("  SOLUTIONS:")
            print("  1. Check if LANGSMITH_WORKSPACE_ID is correct.")
            print("  2. Ensure your API Key belongs to the same Organization as the Workspace.")
            print("  3. Try creating a new API Key from https://smith.langchain.com/settings")
        elif e.response.status_code == 401:
            print("❌ Connection FAILED: 401 Unauthorized")
            print("  ROOT CAUSE: The API Key is invalid or expired.")
            print("  SOLUTION: Generate a new API Key at https://smith.langchain.com/settings")
        else:
            print(f"❌ Connection FAILED: {e}")
    except Exception as e:
        print(f"❌ Connection FAILED: {str(e)}")
        if "403" in str(e):
             print("  ROOT CAUSE: The API Key does not have permission to access the specified Workspace.")
except ImportError:
    print("⚠️  Could not import langsmith. Run 'uv sync' to install dependencies.")


