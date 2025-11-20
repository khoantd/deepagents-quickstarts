"""Research Tools.

This module provides search and content processing utilities for the research agent,
using Tavily for URL discovery and fetching full webpage content, and LightRAG
for knowledge base queries and document management.
"""

import json
import os
import re
from pathlib import Path

import httpx
from langchain_core.tools import InjectedToolArg, tool
from markdownify import markdownify
from tavily import TavilyClient
from typing_extensions import Annotated, Literal

from research_agent.lightrag_client import LightRAGClient

tavily_client = TavilyClient()

# Initialize LightRAG client if configured
_lightrag_client = None
try:
    api_url = os.getenv("LIGHTRAG_API_URL")
    api_key = os.getenv("LIGHTRAG_API_KEY")
    if api_url or api_key:
        _lightrag_client = LightRAGClient(api_url=api_url, api_key=api_key)
except Exception:
    # LightRAG is optional - continue without it if initialization fails
    pass


def sanitize_for_json(text: str) -> str:
    """Sanitize text to ensure it can be safely serialized to JSON.
    
    Removes or fixes invalid escape sequences that would cause JSON parsing
    errors on the client side. The function ensures the string can be safely
    serialized by Python's json module without producing invalid JSON.
    
    Key fixes:
    - Removes invalid escape sequences (e.g., \\x becomes x)
    - Fixes incomplete Unicode escapes (\\u not followed by 4 hex digits)
    - Handles backslashes at end of lines/strings
    - Removes problematic control characters
    
    Args:
        text: The text to sanitize
    
    Returns:
        Sanitized text safe for JSON serialization
    """
    if not text:
        return text
    
    # Fix incomplete Unicode escape sequences (\u not followed by 4 hex digits)
    def fix_unicode_escape(match):
        start_pos = match.end()
        remaining = text[start_pos:]
        if len(remaining) >= 4:
            next_4 = remaining[:4]
            if all(c in '0123456789abcdefABCDEF' for c in next_4):
                # Valid unicode escape, keep it
                return match.group(0)
        # Invalid unicode escape - remove the backslash, keep 'u'
        return 'u'
    
    text = re.sub(r'\\u(?![0-9a-fA-F]{4})', fix_unicode_escape, text)
    
    # Fix invalid escape sequences (backslash not followed by valid escape char)
    # Valid escape sequences in JSON: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
    def fix_escape(match):
        char = match.group(1)
        # If it's already a valid escape sequence, keep it
        if char in ['"', '\\', '/', 'b', 'f', 'n', 'r', 't']:
            return match.group(0)
        # Otherwise, replace with just the character (remove the backslash)
        return char
    
    # Fix invalid escape sequences (excluding 'u' which we handle separately above)
    text = re.sub(r'\\([^"\\/bfnrtu])', fix_escape, text)
    
    # Also handle cases where backslash is at end of line or string (invalid)
    text = re.sub(r'\\\n', '\n', text)
    text = re.sub(r'\\\r', '\r', text)
    text = re.sub(r'\\$', '', text)  # Backslash at end of string
    
    # Verify the result can be safely serialized to JSON
    try:
        # Test serialization - if this works, the string is safe
        json.dumps(text)
    except (TypeError, ValueError, UnicodeEncodeError):
        # If serialization still fails, remove any remaining problematic characters
        # This is a last resort - should rarely be needed
        text = ''.join(
            char if (char.isprintable() or char in '\n\r\t') else ' '
            for char in text
        )
    
    return text


def fetch_webpage_content(url: str, timeout: float = 10.0) -> str:
    """Fetch and convert webpage content to markdown.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Webpage content as markdown
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = httpx.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        content = markdownify(response.text)
        # Sanitize content to ensure it's JSON-safe
        return sanitize_for_json(content)
    except Exception as e:
        error_msg = str(e)
        # Sanitize error message as well
        return sanitize_for_json(f"Error fetching content from {url}: {error_msg}")


@tool(parse_docstring=True)
def tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 1,
    topic: Annotated[
        Literal["general", "news", "finance"], InjectedToolArg
    ] = "general",
) -> str:
    """Search the web for information on a given query.

    Uses Tavily to discover relevant URLs, then fetches and returns full webpage content as markdown.

    Args:
        query: Search query to execute
        max_results: Maximum number of results to return (default: 1)
        topic: Topic filter - 'general', 'news', or 'finance' (default: 'general')

    Returns:
        Formatted search results with full webpage content
    """
    # Use Tavily to discover URLs
    search_results = tavily_client.search(
        query,
        max_results=max_results,
        topic=topic,
    )

    # Fetch full content for each URL
    result_texts = []
    for result in search_results.get("results", []):
        url = result["url"]
        title = result["title"]

        # Fetch webpage content
        content = fetch_webpage_content(url)

        result_text = f"""## {title}
**URL:** {url}

{content}

---
"""
        result_texts.append(result_text)

    # Format final response
    response = f"""🔍 Found {len(result_texts)} result(s) for '{query}':

{chr(10).join(result_texts)}"""

    # Sanitize the final response to ensure JSON safety
    return sanitize_for_json(response)


@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    result = f"Reflection recorded: {reflection}"
    return sanitize_for_json(result)


@tool(parse_docstring=True)
def lightrag_query(
    query: str,
    mode: Annotated[
        Literal["local", "global", "hybrid", "naive", "mix", "bypass"],
        InjectedToolArg,
    ] = "mix",
    top_k: Annotated[int, InjectedToolArg] = 5,
    chunk_top_k: Annotated[int, InjectedToolArg] = 10,
) -> str:
    """Query the LightRAG knowledge base for stored information.

    Use this tool to search for information that has been previously stored in the
    LightRAG knowledge base. This is useful for retrieving information from documents
    that have been uploaded or text that has been inserted into the system.

    Query modes:
    - 'mix' (default): Balanced retrieval using both entities and relationships
    - 'local': Entity-based retrieval, focuses on specific entities
    - 'global': Relationship-based retrieval, focuses on connections between entities
    - 'hybrid': Combines local and global retrieval
    - 'naive': Simple retrieval without graph structure
    - 'bypass': Direct query without RAG enhancement

    Args:
        query: The query text to search for in the knowledge base
        mode: Query mode - 'local', 'global', 'hybrid', 'naive', 'mix', or 'bypass' (default: 'mix')
        top_k: Number of top items to retrieve (default: 5)
        chunk_top_k: Number of text chunks to retrieve from vector search (default: 10)

    Returns:
        Query response with retrieved information and generated answer
    """
    if not _lightrag_client:
        return "Error: LightRAG is not configured. Please set LIGHTRAG_API_URL and/or LIGHTRAG_API_KEY environment variables."

    try:
        response = _lightrag_client.query(
            query=query,
            mode=mode,
            top_k=top_k,
            chunk_top_k=chunk_top_k,
        )
        result = response.get("response", "No response generated")
        return sanitize_for_json(result) if isinstance(result, str) else str(result)
    except Exception as e:
        error_msg = str(e)
        return sanitize_for_json(f"Error querying LightRAG: {error_msg}")


@tool(parse_docstring=True)
def lightrag_insert_text(text: str) -> str:
    """Insert text into the LightRAG knowledge base for later retrieval.

    Use this tool to store research findings, summaries, or important information
    into the knowledge base so it can be retrieved later using lightrag_query.

    Args:
        text: Text content to insert into the knowledge base

    Returns:
        Status message indicating success or failure
    """
    if not _lightrag_client:
        return "Error: LightRAG is not configured. Please set LIGHTRAG_API_URL and/or LIGHTRAG_API_KEY environment variables."

    try:
        response = _lightrag_client.insert_text(text=text)
        status = response.get("status", "unknown")
        message = response.get("message", "")
        if status == "success":
            result = f"Successfully inserted text into LightRAG knowledge base. {message}"
        else:
            result = f"Insert status: {status}. {message}"
        return sanitize_for_json(result)
    except Exception as e:
        error_msg = str(e)
        return sanitize_for_json(f"Error inserting text into LightRAG: {error_msg}")


@tool(parse_docstring=True)
def lightrag_upload_document(file_path: str) -> str:
    """Upload a file to the LightRAG knowledge base for indexing.

    Use this tool to upload documents (PDF, text files, etc.) to the knowledge base.
    The document will be processed and indexed for later retrieval.

    Args:
        file_path: Path to the file to upload (relative to current working directory or absolute path)

    Returns:
        Status message indicating success or failure
    """
    if not _lightrag_client:
        return "Error: LightRAG is not configured. Please set LIGHTRAG_API_URL and/or LIGHTRAG_API_KEY environment variables."

    try:
        # Resolve file path
        path = Path(file_path)
        if not path.is_absolute():
            # Try relative to current working directory
            path = Path.cwd() / path

        response = _lightrag_client.upload_document(str(path))
        status = response.get("status", "unknown")
        message = response.get("message", "")
        if status == "success":
            result = f"Successfully uploaded document to LightRAG. {message}"
        elif status == "duplicated":
            result = f"Document already exists in LightRAG. {message}"
        else:
            result = f"Upload status: {status}. {message}"
        return sanitize_for_json(result)
    except ValueError as e:
        error_msg = str(e)
        return sanitize_for_json(f"Error: {error_msg}")
    except Exception as e:
        error_msg = str(e)
        return sanitize_for_json(f"Error uploading document to LightRAG: {error_msg}")


@tool(parse_docstring=True)
def lightrag_get_status() -> str:
    """Get the status of documents and pipeline in the LightRAG knowledge base.

    Use this tool to check:
    - Document processing status (pending, processing, processed, failed)
    - Pipeline status (busy, progress, current job)

    Returns:
        Formatted status information about documents and pipeline
    """
    if not _lightrag_client:
        return "Error: LightRAG is not configured. Please set LIGHTRAG_API_URL and/or LIGHTRAG_API_KEY environment variables."

    try:
        # Get document statuses
        docs_response = _lightrag_client.get_documents()
        pipeline_response = _lightrag_client.get_pipeline_status()

        # Format document statuses
        status_lines = ["## Document Status"]
        if "statuses" in docs_response:
            for status, docs in docs_response["statuses"].items():
                count = len(docs) if isinstance(docs, list) else 0
                status_lines.append(f"- {status}: {count} document(s)")

        # Format pipeline status
        status_lines.append("\n## Pipeline Status")
        busy = pipeline_response.get("busy", False)
        job_name = pipeline_response.get("job_name", "No active job")
        cur_batch = pipeline_response.get("cur_batch", 0)
        batchs = pipeline_response.get("batchs", 0)
        docs = pipeline_response.get("docs", 0)
        latest_message = pipeline_response.get("latest_message", "")

        status_lines.append(f"- Busy: {busy}")
        status_lines.append(f"- Current Job: {job_name}")
        if batchs > 0:
            status_lines.append(f"- Progress: Batch {cur_batch} of {batchs}")
        if docs > 0:
            status_lines.append(f"- Total Documents: {docs}")
        if latest_message:
            status_lines.append(f"- Latest Message: {latest_message}")

        result = "\n".join(status_lines)
        return sanitize_for_json(result)
    except Exception as e:
        error_msg = str(e)
        return sanitize_for_json(f"Error getting LightRAG status: {error_msg}")
