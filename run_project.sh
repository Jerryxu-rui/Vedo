#!/bin/bash

# ViMax Project Runner
# This script helps you run both backend and frontend servers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     ViMax Project Runner               ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo ""

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    echo -e "${YELLOW}Killing process on port $port...${NC}"
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
}

# Check Python environment
echo -e "${BLUE}[1/4] Checking Python environment...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "${RED}Error: Python virtual environment not found!${NC}"
    echo -e "${YELLOW}Please run: uv venv && uv pip install -e .${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python environment found${NC}"
echo ""

# Check frontend dependencies
echo -e "${BLUE}[2/4] Checking frontend dependencies...${NC}"
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    cd frontend && npm install && cd ..
fi
echo -e "${GREEN}✓ Frontend dependencies ready${NC}"
echo ""

# Check ports
echo -e "${BLUE}[3/4] Checking ports...${NC}"
if check_port 8091; then
    echo -e "${YELLOW}Port 8091 (backend) is in use${NC}"
    read -p "Kill the process? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill_port 8091
    fi
fi

if check_port 5173; then
    echo -e "${YELLOW}Port 5173 (frontend) is in use${NC}"
    read -p "Kill the process? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill_port 5173
    fi
fi
echo -e "${GREEN}✓ Ports available${NC}"
echo ""

# Menu
echo -e "${BLUE}[4/4] Select what to run:${NC}"
echo "  1) Backend only (port 8091)"
echo "  2) Frontend only (port 5173)"
echo "  3) Both (recommended)"
echo "  4) Exit"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo -e "${GREEN}Starting backend server on port 8091...${NC}"
        echo -e "${YELLOW}Note: You need to implement the backend server first!${NC}"
        echo -e "${YELLOW}Example: uvicorn main:app --host 0.0.0.0 --port 8091 --reload${NC}"
        source .venv/bin/activate
        # Add your backend start command here
        # python main_script2video.py
        ;;
    2)
        echo -e "${GREEN}Starting frontend server on port 5173...${NC}"
        cd frontend
        npm run dev
        ;;
    3)
        echo -e "${GREEN}Starting both servers...${NC}"
        echo -e "${YELLOW}Backend: http://localhost:8091${NC}"
        echo -e "${YELLOW}Frontend: http://localhost:5173${NC}"
        echo ""
        
        # Start backend in background
        echo -e "${BLUE}Starting backend...${NC}"
        source .venv/bin/activate
        # Add your backend start command here
        # python main_script2video.py &
        # BACKEND_PID=$!
        
        # Wait a bit for backend to start
        sleep 2
        
        # Start frontend
        echo -e "${BLUE}Starting frontend...${NC}"
        cd frontend
        npm run dev
        
        # Cleanup on exit
        # trap "kill $BACKEND_PID 2>/dev/null" EXIT
        ;;
    4)
        echo -e "${BLUE}Exiting...${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac