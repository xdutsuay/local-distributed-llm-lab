# Testing & Verification Strategy

This document outlines the testing strategy for LLM Lab, covering Unit Tests, Integration Tests, and E2E Tests.

## Overview
We use `pytest` as our primary test runner. Tests are strictly categorized to differentiate between fast unit tests and slower integration tests involving Ray/Selenium.

## Test Directory Structure
- `tests/`: Unit and component integration tests.
- `tests/e2e/`: Full stack integration tests (Ray + FastAPI + Browser).

## Running Tests

### 1. Functional / Unit Tests
Fast tests for logic, routing, and components.
```bash
pytest tests/ --ignore=tests/test_mcp.py
```

### 2. End-to-End (E2E) Tests
Spin up the full environment. Requires Chrome/Chromedriver.
```bash
./scripts/run_e2e_tests.sh
```
Comprehensive test suite for the Local Distributed LLM Lab project.

## Test Organization

### Core Tests (Implemented)
- **test_routes.py** - FastAPI route validation, redirects, duplication checks
- **test_heartbeat.py** - Node lifecycle, heartbeat mechanism, TTL expiration
- **test_cluster.py** - Ray cluster integration, worker registration
- **test_polish.py** - Attribution metrics, composition tracking

### Integration Tests (Partially Implemented)
- **test_load_balancing.py** - Multi-node distribution, parallel execution (mostly TODOs)
- **test_persistence.py** - Data persistence, state recovery (partially implemented)

### Future Feature Tests (TODOs)
- **test_cache.py** - Phase 11: Mobile node caching and replication
- Additional tests for auto-detection, dynamic routing

## Running Tests

### All Tests
```bash
python -m pytest tests/
```

### Specific Test File
```bash
python -m pytest tests/test_routes.py -v
```

### Skip Future Feature Tests
```bash
python -m pytest tests/ -k "not skip"
```

### Coverage Report
```bash
python -m pytest tests/ --cov=coordinator --cov-report=html
```

## Test Coverage Goals

- [x] Route validation and accessibility
- [x] Heartbeat mechanism
- [x] Node registration
- [x] Task attribution
- [ ] Load balancing (ISSUE-001)
- [ ] Mobile caching (Phase 11)
- [ ] Cache replication (Phase 11)
- [ ] Distributed state persistence
- [ ] Auto-model detection

## CI/CD Integration
These tests are designed to run in CI/CD pipelines. Skipped tests indicate features planned for future implementation.
