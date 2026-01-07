#!/bin/bash

# ViMax Project - Complete Restart Script
# Restarts both backend API server and frontend dev server

set -e  # Exit on error

echo "=========================================="
echo "ViMax Project - Complete Restart"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to kill processes
kill_processes() {
    local process_name=$1
    local pids=$(ps aux | grep "$process_name" | grep -v grep | awk '{print $2}')
    
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}Stopping $process_name processes...${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 2
        echo -e "${GREEN}✓ Stopped $process_name${NC}"
    else
        echo -e "${YELLOW}No $process_name processes found${NC}"
    fi
}

# Function to wait for port to be free
wait_for_port_free() {
    local port=$1
    local max_wait=10
    local waited=0
    
    while lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; do
        if [ $waited -ge $max_wait ]; then
            echo -e "${RED}✗ Port $port still in use after ${max_wait}s${NC}"
            return 1
        fi
        echo "Waiting for port $port to be free..."
        sleep 1
        waited=$((waited + 1))
    done
    
    echo -e "${GREEN}✓ Port $port is free${NC}"
    return 0
}

# Step 1: Stop existing processes
echo "Step 1: Stopping existing processes..."
echo "--------------------------------------"

# Stop backend
kill_processes "api_server.py"
kill_processes "uvicorn"

# Stop frontend
kill_processes "vite"
kill_processes "npm.*dev"

# Force kill anything on ports 3001 and 5000
echo "Force killing processes on ports 3001 and 5000..."
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
lsof -ti:5000 | xargs kill -9 2>/dev/null || true
sleep 2

echo ""

# Wait for ports to be free
echo "Waiting for ports to be released..."
wait_for_port_free 3001 || {
    echo -e "${RED}Trying to force kill port 3001 again...${NC}"
    fuser -k 3001/tcp 2>/dev/null || true
    sleep 2
    wait_for_port_free 3001 || exit 1
}
wait_for_port_free 5000 || {
    echo -e "${RED}Trying to force kill port 5000 again...${NC}"
    fuser -k 5000/tcp 2>/dev/null || true
    sleep 2
    wait_for_port_free 5000 || exit 1
}

echo ""

# Step 2: Start backend
echo "Step 2: Starting backend API server..."
echo "--------------------------------------"

if [ ! -f "api_server.py" ]; then
    echo -e "${RED}✗ Error: api_server.py not found${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}✗ Error: Virtual environment not found${NC}"
    echo "Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Start backend in background
echo "Starting backend on port 3001..."
nohup bash start_api_server.sh > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to initialize..."
sleep 3

# Check if backend is running
if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}✓ Backend started successfully (PID: $BACKEND_PID)${NC}"
    
    # Test backend health
    if curl -s http://localhost:3001/health > /dev/null 2>&1 || curl -s http://localhost:3001/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is responding${NC}"
    else
        echo -e "${YELLOW}⚠ Backend started but not responding yet (may need more time)${NC}"
    fi
else
    echo -e "${RED}✗ Backend failed to start${NC}"
    echo "Check backend.log for errors"
    exit 1
fi

echo ""

# Step 3: Start frontend
echo "Step 3: Starting frontend dev server..."
echo "--------------------------------------"

if [ ! -d "frontend" ]; then
    echo -e "${RED}✗ Error: frontend directory not found${NC}"
    exit 1
fi

cd frontend

# Check Node.js version
NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    echo -e "${RED}✗ Error: Node.js version $NODE_VERSION is too old${NC}"
    echo "Please upgrade to Node.js v16+ or v18+ (LTS)"
    echo "Current version: $(node --version)"
    echo ""
    echo "To upgrade Node.js:"
    echo "  1. Using nvm: nvm install 18 && nvm use 18"
    echo "  2. Or download from: https://nodejs.org/"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start frontend in background
echo "Starting frontend on port 5000..."
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
echo "Waiting for frontend to initialize..."
sleep 5

# Check if frontend is running
if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}✓ Frontend started successfully (PID: $FRONTEND_PID)${NC}"
    
    # Test frontend health
    if curl -s http://localhost:5000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend is responding${NC}"
    else
        echo -e "${YELLOW}⚠ Frontend started but not responding yet (may need more time)${NC}"
    fi
else
    echo -e "${RED}✗ Frontend failed to start${NC}"
    echo "Check frontend.log for errors"
    cd ..
    exit 1
fi

cd ..

echo ""
echo "=========================================="
echo "✓ All services started successfully!"
echo "=========================================="
echo ""
echo "Service Status:"
echo "  • Backend API:  http://localhost:3001"
echo "  • Frontend UI:  http://localhost:5000"
echo ""
echo "Logs:"
echo "  • Backend:  tail -f backend.log"
echo "  • Frontend: tail -f frontend.log"
echo ""
echo "To stop all services:"
echo "  pkill -f 'api_server.py|uvicorn|vite|npm.*dev'"
echo ""
echo "=========================================="