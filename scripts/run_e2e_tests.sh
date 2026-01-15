#!/bin/bash
# Run end-to-end integration tests
# This script starts the full stack and runs Selenium tests

set -e

echo "🧪 Running End-to-End Integration Tests"
echo "========================================"
echo ""

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
echo "📦 Checking dependencies..."
pip install -q selenium pytest-selenium webdriver-manager pytest-timeout

# Run E2E tests
echo ""
echo "🚀 Starting E2E tests (this will start Ray + FastAPI + Browser)..."
echo ""

# Run with verbose output and show print statements
pytest tests/e2e/ -v -s --tb=short --timeout=180

echo ""
echo "✅ E2E tests complete!"
