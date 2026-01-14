"""
Tests for FastAPI routes, redirects, and port configuration
"""
import pytest
from httpx import AsyncClient, ASGITransport
from coordinator.main import app


@pytest.mark.asyncio
async def test_all_routes_exist():
    """Verify all documented routes are accessible"""
    routes = [
        "/",
        "/llmlab",
        "/nodes",
        "/chat_ui",
        "/memo",
        "/health",
        "/api/nodes",
        "/api/tasks",
        "/api/memo",
    ]
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for route in routes:
            response = await ac.get(route)
            assert response.status_code in [200, 405], f"Route {route} failed with {response.status_code}"


@pytest.mark.asyncio
async def test_no_route_duplication():
    """Ensure no duplicate route definitions (same path + method)"""
    # Filter out FastAPI auto-generated routes
    user_routes = [
        route for route in app.routes 
        if not route.path.startswith('/docs') 
        and not route.path.startswith('/openapi')
        and not route.path.startswith('/redoc')
        and route.path != '/static'
    ]
    
    # Build path+method combinations
    route_signatures = []
    for route in user_routes:
        if hasattr(route, 'methods'):
            for method in route.methods:
                route_signatures.append(f"{method}:{route.path}")
        else:
            route_signatures.append(f"MOUNT:{route.path}")
    
    # Check for duplicates
    assert len(route_signatures) == len(set(route_signatures)), \
        f"Duplicate routes detected: {[sig for sig in route_signatures if route_signatures.count(sig) > 1]}"


@pytest.mark.asyncio
async def test_dashboard_redirect():
    """Test that /nodes redirects to dashboard correctly"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Both should serve the same HTML
        nodes_response = await ac.get("/nodes")
        llmlab_response = await ac.get("/llmlab")
        
        assert nodes_response.status_code == 200
        assert llmlab_response.status_code == 200


@pytest.mark.asyncio
async def test_api_endpoints_return_json():
    """Verify API endpoints return JSON"""
    api_endpoints = ["/api/nodes", "/api/tasks", "/api/memo"]
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for endpoint in api_endpoints:
            response = await ac.get(endpoint)
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "ray_status" in data
