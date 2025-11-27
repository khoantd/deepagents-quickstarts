# Research Service

Web service for the deep research agent that exposes REST and gRPC APIs with streaming support.

## Features

- **REST API** with Server-Sent Events (SSE) streaming
- **gRPC API** with server streaming
- Real-time progress updates during research execution
- Support for custom sub-agents and research limits

## Setup

1. Install dependencies:
```bash
cd /path/to/deep_research
uv sync
```

2. Generate protobuf files (if not already generated):
```bash
cd research_service
./generate_proto.sh
# Or manually:
uv run python -m grpc_tools.protoc -I proto --python_out=proto --grpc_python_out=proto proto/research_service.proto
```

3. Set environment variables (in `.env` file):
```bash
# LLM and tool API keys
ANTHROPIC_API_KEY=your_key
TAVILY_API_KEY=your_key
OPENAI_API_KEY=your_key  # if using OpenAI models

# JWT Authentication (Required)
JWT_SECRET_KEY=your-very-secure-secret-key-here-minimum-32-characters
API_KEYS=api-key-1,api-key-2,api-key-3  # Comma-separated list of valid API keys

# Optional JWT settings
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30  # Token expiration in minutes (default: 30)
JWT_ALGORITHM=HS256  # JWT algorithm (default: HS256)
```

**Note**: See [JWT Setup Guide](../docs/jwt_setup.md) for detailed authentication setup instructions.

## Running the Service

Start both HTTP and gRPC servers:

```bash
cd /path/to/deep_research
uv run python research_service/run.py
```

The service will start:
- HTTP server on `http://0.0.0.0:8081` (configurable via `RESEARCH_SERVICE_HTTP_PORT`)
- gRPC server on `0.0.0.0:50052` (configurable via `RESEARCH_SERVICE_GRPC_PORT`)

## API Usage

### Authentication

All endpoints except `/research/healthz` require JWT authentication. See the [JWT Setup Guide](../docs/jwt_setup.md) for detailed instructions.

**Quick Start:**

1. Get a JWT token using an API key:
```bash
curl -X POST http://localhost:8081/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "api-key-1"}'
```

2. Use the token in the `Authorization` header for all protected endpoints:
```bash
TOKEN="your-jwt-token-here"
```

### REST API

#### Synchronous Research
```bash
curl -X POST http://localhost:8081/research \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is quantum computing?",
    "max_concurrent_research_units": 2,
    "max_researcher_iterations": 3
  }'
```

#### Streaming Research (SSE)
```bash
curl -X POST http://localhost:8081/research/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is quantum computing?"
  }'
```

#### List Sub-Agents
```bash
curl -X GET http://localhost:8081/research/sub-agents \
  -H "Authorization: Bearer $TOKEN"
```

#### Health Check (Public - No Authentication Required)
```bash
curl http://localhost:8081/research/healthz
```

### gRPC API

See the generated `research_service_pb2_grpc.py` for client examples. The service provides:
- `Research`: Synchronous research execution
- `ResearchStream`: Streaming research with real-time events

## Request Schema

```python
{
  "query": str,  # Required: Research question
  "sub_agent": str | None,  # Optional: Specific sub-agent to use
  "max_concurrent_research_units": int | None,  # Optional: Max parallel sub-agents (1-5)
  "max_researcher_iterations": int | None,  # Optional: Max delegation rounds (1-5)
  "metadata": dict | None  # Optional: Additional metadata
}
```

## Response Schema

### ResearchResponse (Synchronous)
```python
{
  "query": str,
  "report": str | None,  # Final report from /final_report.md
  "final_message": str | None,  # Final agent message if report unavailable
  "metadata": dict,  # Tool calls, sub-agents used, etc.
  "completed_at": datetime
}
```

### ResearchEvent (Streaming)
```python
{
  "event_type": str,  # research_started, tool_call, tool_result, progress, report_available, research_completed, error
  "timestamp": datetime,
  "data": dict  # Event-specific data
}
```

## Event Types

- `research_started`: Research task initiated
- `tool_call`: Tool invocation (tavily_search, think_tool, etc.)
- `tool_result`: Tool execution result
- `sub_agent_delegated`: Sub-agent task created
- `sub_agent_result`: Sub-agent findings received
- `progress`: General progress updates
- `report_available`: Final report written to `/final_report.md`
- `research_completed`: Research finished with final report content
- `error`: Error occurred during research

## Configuration

Environment variables:

### Service Configuration
- `RESEARCH_SERVICE_HTTP_HOST`: HTTP server host (default: `0.0.0.0`)
- `RESEARCH_SERVICE_HTTP_PORT`: HTTP server port (default: `8081`)
- `RESEARCH_SERVICE_GRPC_HOST`: gRPC server host (default: `0.0.0.0`)
- `RESEARCH_SERVICE_GRPC_PORT`: gRPC server port (default: `50052`)
- `RESEARCH_SERVICE_RELOAD`: Enable auto-reload (default: `true`)
- `RESEARCH_SERVICE_ENV`: Environment (local/staging/production, default: `local`)

### JWT Authentication (Required)
- `JWT_SECRET_KEY`: Secret key for signing JWT tokens (required)
- `API_KEYS`: Comma-separated list of valid API keys (required)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration in minutes (optional, default: `30`)
- `JWT_ALGORITHM`: JWT algorithm (optional, default: `HS256`)
- `JWT_ISSUER`: Optional issuer claim for tokens

See [JWT Setup Guide](../docs/jwt_setup.md) for complete authentication documentation.

## Notes

- The service runs the agent in-process
- Final reports are written to `/final_report.md` (may need adjustment for production)
- Agent execution uses LangGraph's `astream_events()` API for streaming
- Tool calls and sub-agent results are captured and streamed in real-time

