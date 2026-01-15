"""
Tests for mobile PWA features including wake lock
"""
import pytest
from httpx import AsyncClient, ASGITransport
from coordinator.main import app


@pytest.mark.asyncio
async def test_mobile_pwa_landing_page():
    """Test that mobile PWA landing page loads"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"LLM Lab Worker" in response.content


@pytest.mark.asyncio
async def test_mobile_pwa_has_wake_lock_button():
    """Test that wake lock button is present in PWA"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
        
        assert response.status_code == 200
        assert b"toggleWakeLock" in response.content
        assert b"wakeBtn" in response.content


@pytest.mark.asyncio
async def test_mobile_pwa_has_wake_lock_function():
    """Test that wake lock JavaScript function exists"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
        
        assert response.status_code == 200
        # Check wake lock implementation
        assert b"navigator.wakeLock.request" in response.content
        assert b"wakeLock.release" in response.content


@pytest.mark.asyncio
async def test_mobile_pwa_has_heartbeat():
    """Test that mobile PWA sends heartbeats"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
        
        assert response.status_code == 200
        # Check heartbeat functionality
        assert b"setInterval" in response.content
        assert b"heartbeat" in response.content


@pytest.mark.asyncio
async def test_mobile_pwa_has_node_id():
    """Test that mobile PWA generates/stores node ID"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
        
        assert response.status_code == 200
        # Check node ID generation
        assert b"localStorage.getItem" in response.content
        assert b"llm_node_id" in response.content


@pytest.mark.asyncio
async def test_mobile_pwa_manifest():
    """Test that PWA manifest exists"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/static/manifest.json")
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_websocket_join_endpoint_exists():
    """Test that WebSocket join endpoint is available"""
    # Note: Can't easily test WebSocket in pytest without special setup
    # This just verifies the endpoint is registered
    from coordinator.main import app
    
    routes = [route.path for route in app.routes]
    assert "/ws/join" in routes
