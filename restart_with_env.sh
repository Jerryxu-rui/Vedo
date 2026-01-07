#!/bin/bash

# Kill any existing server
pkill -f "uvicorn api_server:app" 2>/dev/null || true
sleep 2

# Load environment variables from .env
if [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
    echo "✓ YUNWU_API_KEY loaded"
else
    echo "ERROR: .env file not found!"
    exit 1
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "ERROR: venv not found!"
    exit 1
fi

# Start server in background
echo "Starting server on http://localhost:3001..."
nohup uvicorn api_server:app --host 0.0.0.0 --port 3001 >> server.log 2>&1 &

# Wait for server to start
sleep 3

# Check if server is running
if curl -s http://localhost:3001/health > /dev/null; then
    echo "✓ Server started successfully!"
    echo "  Backend: http://localhost:3001"
    echo "  API Docs: http://localhost:3001/docs"
else
    echo "✗ Server failed to start. Check server.log for details."
    exit 1
fi