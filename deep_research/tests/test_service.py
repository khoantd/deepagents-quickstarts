from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from research_service.main import app
from research_service.schemas import ResearchRequest, ResearchResponse, ResearchEvent, ResearchEventType
from datetime import datetime

client = TestClient(app)

def test_healthcheck():
    response = client.get("/research/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("research_service.api.rest.get_research_service")
def test_research_endpoint(mock_get_service):
    # Mock the service and its execute_research_sync method
    mock_service_instance = MagicMock()
    mock_get_service.return_value = mock_service_instance
    
    mock_response = ResearchResponse(
        query="test query",
        report="Test research content",
        metadata={"source": "test"}
    )
    mock_service_instance.execute_research_sync = AsyncMock(return_value=mock_response)

    request_data = {
        "query": "test query"
    }
    
    response = client.post("/research", json=request_data)
    
    assert response.status_code == 200
    assert response.json() == {
        "query": "test query",
        "report": "Test research content",
        "final_message": None,
        "metadata": {"source": "test"},
        "completed_at": mock_response.completed_at.isoformat()
    }
    mock_service_instance.execute_research_sync.assert_called_once()

@patch("research_service.api.rest.get_research_service")
def test_research_stream_endpoint(mock_get_service):
    # Mock the service and its execute_research method
    mock_service_instance = MagicMock()
    mock_get_service.return_value = mock_service_instance

    async def mock_event_generator(request):
        events = [
            ResearchEvent(
                event_type=ResearchEventType.RESEARCH_STARTED,
                data={"message": "Research started"}
            ),
            ResearchEvent(
                event_type=ResearchEventType.PROGRESS,
                data={"message": "Research in progress"}
            ),
            ResearchEvent(
                event_type=ResearchEventType.RESEARCH_COMPLETED,
                data={"report": "Final report"}
            )
        ]
        for event in events:
            yield event

    mock_service_instance.execute_research = mock_event_generator

    request_data = {
        "query": "test query"
    }

    with client.stream("POST", "/research/stream", json=request_data) as response:
        assert response.status_code == 200
        events = list(response.iter_lines())
        
        # Filter out empty lines (keep-alive)
        events = [e for e in events if e]
        
        # Verify we got events
        assert len(events) > 0
        
        # Check for specific event types in the stream
        # Note: SSE format is "event: ...\ndata: ...\n\n"
        # iter_lines() returns lines, so we need to parse or check for substrings
        
        full_stream = "\n".join(events)
        assert "event: research_event" in full_stream
        assert "research_started" in full_stream
        assert "Research started" in full_stream
        assert "progress" in full_stream
        assert "Research in progress" in full_stream
        assert "research_completed" in full_stream
        assert "Final report" in full_stream
