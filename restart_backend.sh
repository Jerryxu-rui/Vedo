#!/bin/bash
# Backend API Server Restart Script
# 后端API服务器重启脚本

echo "🔄 Restarting Backend API Server..."
echo "=================================="

# Kill existing API server process
echo "📍 Stopping existing API server..."
pkill -f "python.*api_server.py"
sleep 2

# Check if process is killed
if pgrep -f "python.*api_server.py" > /dev/null; then
    echo "⚠️  Force killing API server..."
    pkill -9 -f "python.*api_server.py"
    sleep 1
fi

echo "✅ Old server stopped"

# Start new API server
echo "🚀 Starting new API server..."
./venv/bin/python api_server.py > /tmp/api_server.log 2>&1 &

