#!/bin/bash
# ViMax Minimal Installation Script

echo "=================================="
echo "ViMax Minimal Base System Setup"
echo "=================================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✓ uv found"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
uv sync

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Installation complete!"
    echo ""
    echo "Next steps:"
    echo "1. Configure API keys in configs/idea2video.yaml"
    echo "2. Configure API keys in configs/script2video.yaml"
    echo "3. Run: ./start_api_server.sh"
    echo ""
else
    echo "❌ Installation failed. Please check the error messages above."
    exit 1
fi
