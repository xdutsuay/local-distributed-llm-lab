#!/bin/bash
# LLM Lab Feature Verification Checklist

echo "=== 1. RAG Verification ==="
echo "Checking if vector memory is storing data..."
curl -s http://localhost:8000/api/memo | grep "\"text\"" && echo "✅ Vector Store has entries" || echo "❌ Vector Store empty (add items via Memo UI)"

echo -e "\n=== 2. Mobile Mesh Verification ==="
echo "Checking for active mobile nodes..."
curl -s http://localhost:8000/api/nodes | grep "client_ip" && echo "✅ Mobile/Web nodes detected" || echo "⚠️ No mobile nodes active (Open http://localhost:8000/ on a device)"

echo -e "\n=== 3. Restart & Model Swap ==="
echo "Use the Dashboard at http://localhost:8000/llmlab to:"
echo " - Click [Manage Model] to swap models."
echo " - Click [Restart] to restart a worker node."
