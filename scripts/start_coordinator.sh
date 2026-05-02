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
LLMLAB_HOST=${LLMLAB_HOST:-0.0.0.0}
LLMLAB_PORT=${LLMLAB_PORT:-8000}
LAN_IP=$(python - <<'PY'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(('10.255.255.255', 1))
    print(s.getsockname()[0])
except Exception:
    print('127.0.0.1')
finally:
    s.close()
PY
)

echo "🌐 Starting coordinator on http://${LLMLAB_HOST}:${LLMLAB_PORT}"
echo "📊 Dashboard: http://localhost:${LLMLAB_PORT}/llmlab"
echo "💬 Chat UI: http://localhost:${LLMLAB_PORT}/chat_ui"
echo "📱 LAN Chat UI: http://${LAN_IP}:${LLMLAB_PORT}/chat_ui"
echo ""

# Start FastAPI server
uvicorn coordinator.main:app --host "${LLMLAB_HOST}" --port "${LLMLAB_PORT}"
