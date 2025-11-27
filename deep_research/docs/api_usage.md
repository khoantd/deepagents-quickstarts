# Research Service API Usage

This guide explains how external applications can interact with the Research Service API, specifically the streaming endpoint.

## Base URL

Assuming the service is running locally:
`http://localhost:8000`

## Streaming Endpoint

**URL**: `/research/stream`
**Method**: `POST`
**Content-Type**: `application/json`

### Request Body

```json
{
  "query": "Your research query here",
  "max_concurrent_research_units": 3,
  "max_researcher_iterations": 3
}
```

### Response Format

The endpoint returns a **Server-Sent Events (SSE)** stream.
Each event has the type `research_event`.
The `data` field contains a JSON string with:
- `event_type`: Type of event (e.g., `research_started`, `progress`, `research_completed`)
- `timestamp`: ISO 8601 timestamp
- `data`: Event-specific payload

## Examples

### 1. cURL

```bash
curl -N -X POST http://localhost:8000/research/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Latest advancements in solid state batteries",
    "max_concurrent_research_units": 2
  }'
```

### 2. Python (using `httpx`)

Requires `httpx`: `pip install httpx`

```python
import httpx
import json

API_URL = "http://localhost:8000/research/stream"

def run_research(query):
    payload = {"query": query}
    
    with httpx.stream("POST", API_URL, json=payload, timeout=None) as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                # Extract the JSON data from the SSE line
                data_str = line[6:]
                try:
                    event_data = json.loads(data_str)
                    event_type = event_data.get("event_type")
                    content = event_data.get("data")
                    
                    print(f"[{event_type}] {content}")
                    
                    if event_type == "research_completed":
                        print("\n--- Final Report ---\n")
                        print(content.get("report"))
                        
                except json.JSONDecodeError:
                    pass

if __name__ == "__main__":
    run_research("What are the benefits of agentic coding?")
```

### 3. JavaScript / TypeScript (Node.js or Browser)

Using the `fetch` API (modern browsers and Node.js 18+):

```javascript
async function runResearch(query) {
  const response = await fetch('http://localhost:8000/research/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    
    // Process all complete lines
    buffer = lines.pop() || ''; 

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const dataStr = line.slice(6);
        try {
          const eventData = JSON.parse(dataStr);
          console.log(`[${eventData.event_type}]`, eventData.data);
        } catch (e) {
          console.error('Error parsing JSON:', e);
        }
      }
    }
  }
}

runResearch('History of the internet');
```
