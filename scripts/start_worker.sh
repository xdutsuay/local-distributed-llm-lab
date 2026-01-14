#!/bin/bash
# LLM Lab - Worker Node Startup Script

set -e

# Default values
COORDINATOR_IP=${1:-"auto"}
WORKER_MODEL=${OLLAMA_MODEL:-llama3.2}

echo "🔧 Starting LLM Lab Worker..."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Set environment
export OLLAMA_MODEL=$WORKER_MODEL

if [ "$COORDINATOR_IP" = "auto" ]; then
    echo "🔍 Auto-connecting to local Ray cluster..."
    python coordinator/worker.py
else
    echo "📡 Connecting to coordinator at $COORDINATOR_IP:6379..."
    python coordinator/worker.py --address=$COORDINATOR_IP:6379
fi
