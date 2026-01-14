#!/bin/bash
# LLM Lab - Coordinator Startup Script

set -e

echo "🚀 Starting LLM Lab Coordinator..."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if Ray is running
if ! ray status &> /dev/null; then
    echo "📡 Starting Ray head node..."
    RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 ray start --head --port=6379 --dashboard-host=0.0.0.0 --disable-usage-stats
else
    echo "✅ Ray already running"
fi

# Set environment variables
export OLLAMA_MODEL=${OLLAMA_MODEL:-llama3.2}

echo "🌐 Starting coordinator on http://0.0.0.0:8000"
echo "📊 Dashboard: http://localhost:8000/llmlab"
echo "💬 Chat UI: http://localhost:8000/chat_ui"
echo ""

# Start FastAPI server
uvicorn coordinator.main:app --host 0.0.0.0 --port 8000
