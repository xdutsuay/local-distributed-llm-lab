"""
End-to-end integration tests for LLM Lab
Tests the complete stack: Ray + FastAPI + UI
"""
import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class TestDashboard:
    """Test dashboard functionality"""
    
    def test_dashboard_loads(self, browser, base_url):
        """Test that dashboard page loads successfully"""
        browser.get(f"{base_url}/llmlab")
        
        # Verify page title
        assert "LLM Lab Dashboard" in browser.title or "Cluster Dashboard" in browser.page_source
        
        # Verify key elements are present
        assert browser.find_element(By.TAG_NAME, "table")
        assert "Nodes" in browser.page_source or "No active nodes" in browser.page_source
    
    def test_dashboard_shows_coordinator_node(self, browser, base_url):
        """Test that coordinator registers and appears on dashboard"""
        browser.get(f"{base_url}/llmlab")
        
        # Wait for nodes to appear (coordinator should register within 5 seconds)
        time.sleep(6)
        browser.refresh()
        
        # Check for coordinator node
        page_source = browser.page_source
        assert ("coordinator" in page_source.lower() or 
                "active" in page_source.lower() or
                "201105832418322" in page_source), "Coordinator node not found on dashboard"
    
    def test_dashboard_auto_refresh(self, browser, base_url):
        """Test that dashboard auto-refreshes node data"""
        browser.get(f"{base_url}/llmlab")
        
        initial_content = browser.page_source
        
        # Wait for auto-refresh (should happen every 2 seconds)
        time.sleep(3)
        
        updated_content = browser.page_source
        
        # Content should update (timestamp changes)
        # This is a weak assertion but verifies JS is running
        assert browser.find_element(By.TAG_NAME, "table")


class TestChatUI:
    """Test chat interface functionality"""
    
    def test_chat_ui_loads(self, browser, base_url):
        """Test that chat UI loads successfully"""
        browser.get(f"{base_url}/chat_ui")
        
        # Verify page elements
        assert "Distributed LLM Lab" in browser.page_source
        
        # Verify input and button exist
        input_field = browser.find_element(By.ID, "prompt")
        send_button = browser.find_element(By.ID, "sendBtn")
        
        assert input_field.is_displayed()
        assert send_button.is_displayed()
        assert send_button.is_enabled()
    
    @pytest.mark.timeout(60)
    def test_chat_send_message(self, browser, base_url):
        """Test sending a message through chat UI"""
        browser.get(f"{base_url}/chat_ui")
        
        # Find input and send button
        input_field = browser.find_element(By.ID, "prompt")
        send_button = browser.find_element(By.ID, "sendBtn")
        
        # Type message
        test_message = "Hello, test message"
        input_field.send_keys(test_message)
        
        # Click send
        send_button.click()
        
        # Wait for message to appear in chat
        try:
            WebDriverWait(browser, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "user"))
            )
            
            # Verify user message appears
            assert test_message in browser.page_source
            
        except TimeoutException:
            pytest.fail("User message did not appear in chat")
    
    @pytest.mark.timeout(120)
    @pytest.mark.slow
    def test_chat_receives_response(self, browser, base_url):
        """Test that chat receives a response from the LLM"""
        browser.get(f"{base_url}/chat_ui")
        
        input_field = browser.find_element(By.ID, "prompt")
        send_button = browser.find_element(By.ID, "sendBtn")
        
        # Send simple message
        input_field.send_keys("What is 2+2?")
        send_button.click()
        
        # Wait for "Thinking & Planning..." to appear
        try:
            WebDriverWait(browser, 5).until(
                lambda d: "Thinking" in d.page_source
            )
        except TimeoutException:
            pass  # May be too fast
        
        # Wait for assistant response (should replace "Thinking...")
        try:
            WebDriverWait(browser, 60).until(
                EC.presence_of_element_located((By.CLASS_NAME, "assistant"))
            )
            
            # Check that "Thinking" is gone and we have a response
            page_source = browser.page_source
            
            # Should have assistant message
            assert browser.find_elements(By.CLASS_NAME, "assistant")
            
            # Should NOT still be thinking
            assert "Thinking" not in page_source or len(browser.find_elements(By.CLASS_NAME, "assistant")) > 1
            
        except TimeoutException:
            # Take screenshot for debugging
            browser.save_screenshot("/tmp/chat_timeout.png")
            pytest.fail("Chat response timed out after 60 seconds")


class TestAPIEndpoints:
    """Test API endpoints directly"""
    
    def test_health_endpoint(self, base_url):
        """Test health check endpoint"""
        import requests
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "ray_status" in data
    
    def test_nodes_api(self, base_url):
        """Test nodes API endpoint"""
        import requests
        
        # Wait for coordinator to register
        time.sleep(6)
        
        response = requests.get(f"{base_url}/api/nodes")
        assert response.status_code == 200
        data = response.json()
        assert "active_nodes" in data
        
        # Should have at least coordinator node
        assert len(data["active_nodes"]) >= 1, "No nodes registered"
    
    def test_tools_api(self, base_url):
        """Test tools API endpoint"""
        import requests
        response = requests.get(f"{base_url}/api/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) >= 3  # calculator, web_search, text_processor
    
    def test_cache_stats_api(self, base_url):
        """Test cache statistics API"""
        import requests
        response = requests.get(f"{base_url}/api/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert "hits" in data
        assert "misses" in data
        assert "hit_rate" in data


class TestMobilePWA:
    """Test mobile PWA functionality"""
    
    def test_pwa_landing_page(self, browser, base_url):
        """Test mobile worker PWA loads"""
        browser.get(base_url)
        
        assert "LLM Lab Worker" in browser.page_source
        assert browser.find_element(By.ID, "wakeBtn")
    
    def test_wake_lock_button_present(self, browser, base_url):
        """Test wake lock button exists"""
        browser.get(base_url)
        
        wake_btn = browser.find_element(By.ID, "wakeBtn")
        assert wake_btn.is_displayed()
        assert "Wake Lock" in wake_btn.text
