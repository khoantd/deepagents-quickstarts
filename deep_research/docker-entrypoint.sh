#!/bin/bash
# Docker entrypoint script for Deep Research Application
# Supports multiple service modes: langgraph, fastapi, or both

set -o pipefail

# Default service mode
SERVICE_MODE="${SERVICE_MODE:-langgraph}"

echo "🚀 Deep Research Application"
echo "Service Mode: ${SERVICE_MODE}"
echo ""

# Function to run LangGraph server
run_langgraph() {
    echo "📊 Starting LangGraph Server..."
    echo "Server will be available at http://localhost:8123"
    echo ""
    exec uv run langgraph dev
}

# Function to run FastAPI/gRPC service
run_fastapi() {
    echo "🌐 Starting FastAPI/gRPC Service..."
    echo "HTTP API will be available at http://localhost:8081"
    echo "gRPC service will be available at localhost:50052"
    echo ""
    exec uv run python -m research_service.run
}

# Function to run both services
run_both() {
    echo "🔄 Starting both LangGraph and FastAPI/gRPC services..."
    echo ""
    
    # Trap signals to properly cleanup background processes
    cleanup() {
        echo "Shutting down services..."
        kill $LANGRAPH_PID $FASTAPI_PID 2>/dev/null || true
        wait $LANGRAPH_PID $FASTAPI_PID 2>/dev/null || true
        exit 0
    }
    trap cleanup TERM INT
    
    # Start LangGraph in background
    uv run langgraph dev &
    LANGRAPH_PID=$!
    
    # Give LangGraph a moment to start
    sleep 2
    
    # Start FastAPI/gRPC in background
    uv run python -m research_service.run &
    FASTAPI_PID=$!
    
    # Wait for either process to exit (wait -n waits for next process to change state)
    # If either exits, we'll clean up both
    wait -n
    
    # If we get here, one process exited
    echo "One of the services exited, shutting down..."
    cleanup
}

# Route based on service mode
case "${SERVICE_MODE}" in
    langgraph)
        run_langgraph
        ;;
    fastapi)
        run_fastapi
        ;;
    both)
        run_both
        ;;
    *)
        echo "❌ Error: Invalid SERVICE_MODE '${SERVICE_MODE}'"
        echo "Valid options: langgraph, fastapi, or both"
        exit 1
        ;;
esac

