#!/bin/bash
# VERA LLM Worker - Linux Startup Script
# Starts Mistral 7B backend on port 18793

set -e

echo "🚀 Starting VERA LLM Worker..."

# Check if model exists
MODEL_PATH="/opt/vera-office/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
if [ ! -f "$MODEL_PATH" ]; then
    echo "❌ Model not found: $MODEL_PATH"
    exit 1
fi

echo "✅ Model found: $MODEL_PATH"

# Check if port 18793 is in use
if lsof -Pi :18793 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 18793 already in use. LLM Worker may already be running."
    echo "   Use: sudo systemctl stop llm_worker (to stop)"
    exit 1
fi

# Navigate to directory
cd /opt/vera-office/backend/llm_worker

# Activate venv
if [ -f "../../venv/bin/activate" ]; then
    source ../../venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  No virtual environment found, using system Python"
fi

echo "📦 Installing dependencies..."
pip install -q llama-cpp-python fastapi uvicorn pydantic loguru

echo "🔥 Starting LLM Worker on port 18793..."
echo "   Model: Mistral 7B Instruct v0.2"
echo "   Context Window: 8192 tokens"
echo "   CPU Threads: 8"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start server (blocks until Ctrl+C)
python3 server.py
