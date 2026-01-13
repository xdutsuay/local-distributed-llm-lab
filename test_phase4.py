import asyncio
import websockets
import json
import time
import pytest

@pytest.mark.asyncio
async def test_websocket():
    uri = "ws://localhost:8000/ws/join"
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")
        
        # Send heartbeat
        msg = {
            "node_id": "test-mobile-node",
            "capabilities": ["mobile_inference"],
            "model": "gemma-2b",
            "timestamp": time.time()
        }
        await websocket.send(json.dumps(msg))
        print("Sent heartbeat")
        
        # Keep alive for a bit to let registry update
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test_websocket())
