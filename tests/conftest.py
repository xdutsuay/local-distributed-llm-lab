import pytest
from fastapi.testclient import TestClient
from coordinator.main import app
import ray

@pytest.fixture(scope="session")
def ray_init():
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)
    yield
    # ray.shutdown() # Keep it running for speed in local dev

@pytest.fixture
def client(ray_init):
    return TestClient(app)
