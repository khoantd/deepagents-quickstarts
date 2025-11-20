"""LightRAG API Client.

This module provides a client for interacting with the LightRAG Server API,
enabling querying of the RAG knowledge base and document management.
"""

import os
from typing import Any, Dict, List, Optional

import httpx


class LightRAGClient:
    """Client for interacting with LightRAG Server API."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """Initialize LightRAG client.

        Args:
            api_url: Base URL for LightRAG API (defaults to environment variable or default URL)
            api_key: API key for authentication (optional, from environment if not provided)
            timeout: Request timeout in seconds
        """
        self.api_url = (
            api_url
            or os.getenv("LIGHTRAG_API_URL", "https://lightrag-latest-xyu3.onrender.com")
        ).rstrip("/")
        self.api_key = api_key or os.getenv("LIGHTRAG_API_KEY")
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication.

        Returns:
            Dictionary of headers including authentication if available
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to LightRAG API.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            json_data: JSON payload for request
            files: Files to upload (for multipart requests)

        Returns:
            Response JSON data

        Raises:
            httpx.HTTPError: If request fails
            ValueError: If response is invalid
        """
        url = f"{self.api_url}{endpoint}"
        headers = self._get_headers()

        try:
            if files:
                # For file uploads, remove Content-Type header (let httpx set it)
                headers.pop("Content-Type", None)
                response = httpx.request(
                    method=method,
                    url=url,
                    headers=headers,
                    files=files,
                    timeout=self.timeout,
                )
            else:
                response = httpx.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_data,
                    timeout=self.timeout,
                )

            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            raise ValueError(error_msg) from e
        except httpx.RequestError as e:
            raise ValueError(f"Request failed: {str(e)}") from e

    def query(
        self,
        query: str,
        mode: str = "mix",
        top_k: Optional[int] = None,
        chunk_top_k: Optional[int] = None,
        max_entity_tokens: Optional[int] = None,
        max_relation_tokens: Optional[int] = None,
        max_total_tokens: Optional[int] = None,
        only_need_context: Optional[bool] = None,
        only_need_prompt: Optional[bool] = None,
        response_type: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        history_turns: Optional[int] = None,
        enable_rerank: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Query the LightRAG knowledge base.

        Args:
            query: The query text
            mode: Query mode - 'local', 'global', 'hybrid', 'naive', 'mix', or 'bypass'
            top_k: Number of top items to retrieve (entities in 'local' mode, relationships in 'global' mode)
            chunk_top_k: Number of text chunks to retrieve initially from vector search
            max_entity_tokens: Maximum tokens for entity context
            max_relation_tokens: Maximum tokens for relationship context
            max_total_tokens: Maximum total tokens for entire query context
            only_need_context: If True, only returns retrieved context without generating response
            only_need_prompt: If True, only returns generated prompt without producing response
            response_type: Response format (e.g., 'Multiple Paragraphs', 'Single Paragraph', 'Bullet Points')
            conversation_history: Past conversation history [{'role': 'user/assistant', 'content': 'message'}]
            history_turns: Number of conversation turns to consider
            enable_rerank: Enable reranking for retrieved text chunks

        Returns:
            Query response containing the generated response or context
        """
        payload: Dict[str, Any] = {"query": query, "mode": mode}

        if top_k is not None:
            payload["top_k"] = top_k
        if chunk_top_k is not None:
            payload["chunk_top_k"] = chunk_top_k
        if max_entity_tokens is not None:
            payload["max_entity_tokens"] = max_entity_tokens
        if max_relation_tokens is not None:
            payload["max_relation_tokens"] = max_relation_tokens
        if max_total_tokens is not None:
            payload["max_total_tokens"] = max_total_tokens
        if only_need_context is not None:
            payload["only_need_context"] = only_need_context
        if only_need_prompt is not None:
            payload["only_need_prompt"] = only_need_prompt
        if response_type is not None:
            payload["response_type"] = response_type
        if conversation_history is not None:
            payload["conversation_history"] = conversation_history
        if history_turns is not None:
            payload["history_turns"] = history_turns
        if enable_rerank is not None:
            payload["enable_rerank"] = enable_rerank

        return self._make_request("POST", "/query", json_data=payload)

    def insert_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Insert text into the RAG system.

        Args:
            text: Text content to insert
            metadata: Optional metadata dictionary

        Returns:
            Insert response with status
        """
        payload: Dict[str, Any] = {"text": text}
        if metadata:
            payload["metadata"] = metadata

        return self._make_request("POST", "/documents/text", json_data=payload)

    def insert_texts(self, texts: List[str], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Insert multiple texts into the RAG system.

        Args:
            texts: List of text contents to insert
            metadata: Optional metadata dictionary

        Returns:
            Insert response with status
        """
        payload: Dict[str, Any] = {"texts": texts}
        if metadata:
            payload["metadata"] = metadata

        return self._make_request("POST", "/documents/texts", json_data=payload)

    def upload_document(self, file_path: str) -> Dict[str, Any]:
        """Upload a file to the input directory and index it.

        Args:
            file_path: Path to the file to upload

        Returns:
            Upload response with status
        """
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")

        with open(file_path, "rb") as f:
            file_name = os.path.basename(file_path)
            files = {"file": (file_name, f, "application/octet-stream")}
            return self._make_request("POST", "/documents/upload", files=files)

    def get_documents(self) -> Dict[str, Any]:
        """Get the status of all documents in the system.

        Returns:
            Document statuses grouped by processing status
        """
        return self._make_request("GET", "/documents")

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get the current status of the document indexing pipeline.

        Returns:
            Pipeline status including processing state and progress
        """
        return self._make_request("GET", "/documents/pipeline_status")

    def scan_documents(self) -> Dict[str, Any]:
        """Trigger scanning process for new documents.

        Returns:
            Scan response with status and track_id
        """
        return self._make_request("POST", "/documents/scan")

    def delete_document(self, document_id: str, delete_file: bool = False) -> Dict[str, Any]:
        """Delete a document and all its associated data by ID.

        Args:
            document_id: ID of the document to delete
            delete_file: Whether to also delete the source file

        Returns:
            Delete response with status
        """
        payload = {"ids": [document_id], "delete_file": delete_file}
        return self._make_request("DELETE", "/documents/delete_document", json_data=payload)

    def clear_documents(self) -> Dict[str, Any]:
        """Clear all documents from the RAG system.

        Returns:
            Clear response with status and message
        """
        return self._make_request("DELETE", "/documents")

