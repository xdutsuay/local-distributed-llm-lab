# End-to-End Testing

This directory contains integration tests that verify the complete LLM Lab stack.

## What E2E Tests Do

Unlike unit tests, these tests:
- ✅ Start a real Ray cluster
- ✅ Start the FastAPI server
- ✅ Launch a real browser (Chrome with Selenium)
- ✅ Test actual user workflows
- ✅ Verify the entire system works together

## Running E2E Tests

```bash
# Quick run (recommended)
./scripts/run_e2e_tests.sh

# Or manually
source venv/bin/activate
pytest tests/e2e/ -v
```

## Test Categories

### TestDashboard
- Dashboard loads and displays correctly
- Coordinator node registers and appears
- Auto-refresh works

### TestChatUI
- Chat interface loads
- Messages can be sent
- **LLM responses are received** (critical regression test)

### TestAPIEndpoints
- Health checks
- Nodes API
- Tools API  
- Cache stats API

### TestMobilePWA
- PWA landing page
- Wake lock button

## Test Infrastructure

The `conftest.py` file provides:
- `ray_cluster` - Starts/stops Ray for test session
- `fastapi_server` - Starts/stops coordinator API
- `browser` - Provides Selenium WebDriver

## Debugging Failed Tests

If tests fail:
1. Check `/tmp/chat_timeout.png` for browser screenshot
2. Server logs in test output show FastAPI errors
3. Ray logs in test output show worker issues

## Adding New E2E Tests

```python
def test_my_feature(browser, base_url):
    browser.get(f"{base_url}/my-page")
    # Your test here
    assert something
```
