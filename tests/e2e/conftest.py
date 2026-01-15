"""
Conftest for end-to-end integration tests

Sets up full stack: Ray cluster + FastAPI server + Selenium WebDriver
"""
import pytest
import subprocess
import time
import requests
import os
import sys
import signal
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))



@pytest.fixture(scope="session")
def ray_cluster():
    """Start Ray cluster for testing"""
    print("\n🚀 Starting Ray cluster...")
    
    # Kill any existing Ray instances
    subprocess.run(["ray", "stop"], capture_output=True)
    time.sleep(2)
    
    # Start Ray with test configuration
    process = subprocess.Popen(
        ["ray", "start", "--head", "--port=6379", "--dashboard-port=8265"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for Ray to be ready
    time.sleep(5)
    
    # Verify Ray is running
    try:
        result = subprocess.run(["ray", "status"], capture_output=True, text=True, timeout=10)
        if "No cluster running" in result.stdout:
            raise RuntimeError("Ray cluster failed to start")
        print("✅ Ray cluster started successfully")
    except Exception as e:
        print(f"❌ Ray cluster startup failed: {e}")
        raise
    
    yield
    
    # Cleanup
    print("\n🛑 Stopping Ray cluster...")
    subprocess.run(["ray", "stop"], capture_output=True)
    time.sleep(2)


@pytest.fixture(scope="session")
def fastapi_server(ray_cluster):
    """Start FastAPI coordinator server"""
    print("\n🌐 Starting FastAPI server...")
    
    # Kill any process on port 8000
    subprocess.run(["lsof", "-ti:8000"], capture_output=True, check=False)
    subprocess.run(["kill", "-9", "$(lsof -ti:8000)"], shell=True, capture_output=True, check=False)
    time.sleep(2)
    
    # Start uvicorn server
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    process = subprocess.Popen(
        ["uvicorn", "coordinator.main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd="/Users/nehatiwari/localcode/LLMLAB"
    )
    
    # Wait for server to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print("✅ FastAPI server started successfully")
                break
        except requests.exceptions.RequestException:
            if i == max_retries - 1:
                raise RuntimeError("FastAPI server failed to start")
            time.sleep(1)
    
    yield process
    
    # Cleanup
    print("\n🛑 Stopping FastAPI server...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    
    # Extra cleanup
    subprocess.run(["lsof", "-ti:8000"], capture_output=True, check=False)
    subprocess.run(["kill", "-9", "$(lsof -ti:8000)"], shell=True, capture_output=True, check=False)


@pytest.fixture(scope="function")
def browser(fastapi_server):
    """Create Selenium WebDriver for browser testing"""
    print("\n🌐 Starting Chrome WebDriver...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)  # Wait up to 10s for elements
    
    yield driver
    
    # Cleanup
    print("\n🛑 Closing browser...")
    driver.quit()


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application"""
    return "http://localhost:8000"
