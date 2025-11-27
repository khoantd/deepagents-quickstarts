# JWT Authentication Setup Guide

This guide explains how to set up and use JWT authentication for the Research Service API.

## Overview

The Research Service uses JWT (JSON Web Tokens) for API authentication. Users authenticate with API keys to receive JWT tokens, which are then used to access protected endpoints.

## Quick Start

### 1. Set Environment Variables

Add the following environment variables to your `.env` file or export them in your shell:

```bash
# Required: Secret key for signing JWT tokens
# Generate a strong secret key (e.g., using openssl: openssl rand -hex 32)
export JWT_SECRET_KEY=your-very-secure-secret-key-here-minimum-32-characters

# Required: Comma-separated list of valid API keys
# Users will use these API keys to obtain JWT tokens
export API_KEYS=api-key-1,api-key-2,api-key-3

# Optional: Token expiration time in minutes (default: 30)
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Optional: JWT algorithm (default: HS256)
export JWT_ALGORITHM=HS256

# Optional: JWT issuer claim
export JWT_ISSUER=research-service
```

### 2. Generate a Secure Secret Key

Generate a strong secret key for JWT signing:

```bash
# Using OpenSSL
openssl rand -hex 32

# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Important**: Keep your `JWT_SECRET_KEY` secure and never commit it to version control!

### 3. Start the Service

Start the research service as usual:

```bash
# Using the run script
python research_service/run.py

# Or using uvicorn directly
uvicorn research_service.main:app --host 0.0.0.0 --port 8081
```

## Usage

### Step 1: Obtain a JWT Token

Authenticate with an API key to receive a JWT token:

```bash
curl -X POST "http://localhost:8081/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"api_key": "api-key-1"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Step 2: Use the Token to Access Protected Endpoints

Include the JWT token in the `Authorization` header for all protected endpoints:

```bash
# Example: Execute research
curl -X POST "http://localhost:8081/research" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the latest developments in AI?",
    "max_concurrent_research_units": 3
  }'

# Example: List sub-agents
curl -X GET "http://localhost:8081/research/sub-agents" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Example: Stream research events
curl -X POST "http://localhost:8081/research/stream" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"query": "Research topic here"}'
```

### Step 3: Verify Token (Optional)

Verify if a token is still valid:

```bash
curl -X POST "http://localhost:8081/auth/verify" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
{
  "valid": true
}
```

## Public Endpoints

The following endpoint does **not** require authentication:

- `GET /research/healthz` - Health check endpoint

All other endpoints require a valid JWT token.

## Python Client Example

```python
import requests

# Base URL
BASE_URL = "http://localhost:8081"

# Step 1: Get JWT token
response = requests.post(
    f"{BASE_URL}/auth/token",
    json={"api_key": "api-key-1"}
)
token_data = response.json()
access_token = token_data["access_token"]

# Step 2: Use token for authenticated requests
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Execute research
research_response = requests.post(
    f"{BASE_URL}/research",
    headers=headers,
    json={
        "query": "What are the latest developments in AI?",
        "max_concurrent_research_units": 3
    }
)
print(research_response.json())
```

## JavaScript/TypeScript Client Example

```typescript
const BASE_URL = "http://localhost:8081";

// Step 1: Get JWT token
async function getToken(apiKey: string): Promise<string> {
  const response = await fetch(`${BASE_URL}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: apiKey }),
  });
  const data = await response.json();
  return data.access_token;
}

// Step 2: Use token for authenticated requests
async function executeResearch(query: string, token: string) {
  const response = await fetch(`${BASE_URL}/research`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query }),
  });
  return response.json();
}

// Usage
const token = await getToken("api-key-1");
const result = await executeResearch("Research topic", token);
console.log(result);
```

## OpenAPI/Swagger Documentation

When you start the service, visit the interactive API documentation:

- **Swagger UI**: http://localhost:8081/docs
- **ReDoc**: http://localhost:8081/redoc

You can test the authentication flow directly from the Swagger UI:

1. Click the "Authorize" button (lock icon)
2. Enter your JWT token (obtained from `/auth/token`)
3. Click "Authorize"
4. All protected endpoints will now use this token

## Security Best Practices

1. **Strong Secret Key**: Use a cryptographically secure random string (minimum 32 characters) for `JWT_SECRET_KEY`
2. **Secure Storage**: Never commit secrets to version control. Use environment variables or a secrets manager
3. **Token Expiration**: Set appropriate expiration times based on your security requirements
4. **HTTPS in Production**: Always use HTTPS in production to protect tokens in transit
5. **API Key Rotation**: Regularly rotate API keys and update the `API_KEYS` environment variable
6. **Token Storage**: Store tokens securely on the client side (e.g., in memory, secure HTTP-only cookies, or secure storage)

## Troubleshooting

### Error: "Invalid API key"
- Verify that the API key you're using is in the `API_KEYS` environment variable
- Check that the API key matches exactly (no extra spaces or characters)
- Ensure the `API_KEYS` environment variable is set correctly

### Error: "Invalid token" or "Could not validate credentials"
- The token may have expired (check `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`)
- The token may be malformed or invalid
- Verify you're including the token in the `Authorization` header with the `Bearer ` prefix
- Ensure the `JWT_SECRET_KEY` hasn't changed (changing it invalidates all existing tokens)

### Error: "Authentication not configured"
- Ensure `JWT_SECRET_KEY` is set
- Ensure `API_KEYS` is set and contains at least one API key

### Service fails to start
- Check that `JWT_SECRET_KEY` is set (it's required)
- Verify all environment variables are properly formatted
- Check the service logs for specific error messages

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | Yes | - | Secret key for signing JWT tokens |
| `API_KEYS` | Yes | - | Comma-separated list of valid API keys |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | 30 | Token expiration time in minutes |
| `JWT_ALGORITHM` | No | HS256 | JWT signing algorithm |
| `JWT_ISSUER` | No | - | Optional issuer claim for tokens |

## API Endpoints

### Authentication Endpoints

- `POST /auth/token` - Get JWT token (requires API key)
- `POST /auth/verify` - Verify token validity (requires JWT token)

### Protected Research Endpoints

- `POST /research` - Execute synchronous research
- `POST /research/stream` - Stream research events (SSE)
- `GET /research/sub-agents` - List available sub-agents

### Public Endpoints

- `GET /research/healthz` - Health check (no authentication required)

