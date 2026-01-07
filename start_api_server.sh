#!/bin/bash

# Start ViMax API Server
# This script starts the FastAPI backend server for video generation

echo "Starting ViMax API Server..."
echo "================================"
echo ""

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
    echo "✓ Environment variables loaded"
else
    echo "Warning: .env file not found"
    echo "Please create a .env file with your API keys"
fi

echo ""

# Activate Python virtual environment
echo "Activating Python virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
elif [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "Warning: venv/bin/activate not found"
    echo "Attempting to continue without activation..."
    echo "If you encounter errors, please activate your environment manually:"
    echo "  source venv/bin/activate"
fi

echo ""

# Check if uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo "Error: uvicorn is not installed in the environment"
    echo "Please install it with: pip install fastapi uvicorn pydantic"
    exit 1
fi

# Check if FastAPI is installed
if ! python -c "import fastapi" &> /dev/null 2>&1; then
    echo "Error: FastAPI is not installed in the environment"
    echo "Please install it with: pip install fastapi uvicorn pydantic"
    exit 1
fi

echo "✓ All dependencies found"
echo ""

# Start the server
echo "Starting server on http://localhost:3001"
echo "API documentation will be available at http://localhost:3001/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn api_server:app --host 0.0.0.0 --port 3001 --reload