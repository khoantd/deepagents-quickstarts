# Multi-stage Dockerfile for Deep Research Application
# Supports both LangGraph server and FastAPI/gRPC service modes

# Build stage: Install dependencies
FROM python:3.11-slim as builder

# Install system dependencies required for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files and package directories first for better layer caching
# Package directories are needed for setuptools to build the package
COPY pyproject.toml uv.lock* ./
COPY research_agent/ ./research_agent/
COPY research_service/ ./research_service/

# Install dependencies using uv
# Use --frozen if lock file exists, otherwise sync normally
RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-dev; \
    else \
        uv sync --no-dev; \
    fi

# Runtime stage: Minimal image with only necessary files
FROM python:3.11-slim

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv in runtime stage
RUN pip install --no-cache-dir uv

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
# uv creates a .venv directory with all dependencies
COPY --from=builder /app/.venv /app/.venv

# Change ownership of .venv to appuser (needed for editable installs)
RUN chown -R appuser:appuser /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .

# Copy entrypoint script
COPY --chown=appuser:appuser docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SERVICE_MODE=langgraph

# Switch to non-root user
USER appuser

# Expose ports
# LangGraph default port: 8123
# FastAPI default port: 8081
# gRPC default port: 50052
EXPOSE 8123 8081 50052

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

