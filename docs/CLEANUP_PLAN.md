# Proposed Directory Structure (After Cleanup)

```
LLMLAB/
├── README.md
├── requirements.txt
├── pytest.ini
├── .gitignore (updated)
│
├── config/                      # All configuration files
│   ├── antigravity_config.json
│   ├── claude_config_example.json
│   └── .env.example
│
├── coordinator/                 # Core orchestration logic
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── graph.py                # LangGraph workflow
│   ├── planner.py              # Task decomposition
│   ├── worker.py               # Worker actor
│   ├── registry.py             # Node registry
│   └── messaging.py            # Ray message bus
│
├── frontend/                    # UI files
│   ├── index.html              # PWA landing
│   ├── dashboard.html          # Cluster dashboard
│   ├── chat.html               # Chat interface
│   ├── memo.html               # Shared clipboard
│   └── manifest.json
│
├── tests/                       # Test suite (13 files)
│   ├── README.md
│   ├── conftest.py
│   ├── test_routes.py
│   ├── test_heartbeat.py
│   ├── test_cluster.py
│   ├── test_load_balancing.py
│   ├── test_cache.py
│   ├── test_persistence.py
│   └── ... (other tests)
│
├── scripts/                     # NEW - Utility scripts
│   ├── start_coordinator.sh    # Easy coordinator startup
│   ├── start_worker.sh         # Worker startup helper
│   └── health_check.py         # Cluster diagnostics
│
├── docs/                        # Documentation
│   ├── CONNECT_REMOTE.md       # Existing guide
│   └── ARCHITECTURE.md         # NEW - System design doc
│
├── archive/                     # NEW - Historical artifacts
│   ├── historical_plans/
│   │   ├── PLAN.TXT
│   │   └── chatsummary.txt
│   └── debug_scripts/
│       ├── debug_bus.py
│       └── test_phase4.py
│
├── mcp_server.py               # MCP integration (keep for now)
└── assets/                     # Static assets (screenshots, etc.)
```

## Files to Move

### Archive (Historical - No Longer Needed)
- `PLAN.TXT` → `archive/historical_plans/`
- `chatsummary.txt` → `archive/historical_plans/`
- `debug_bus.py` → `archive/debug_scripts/`
- `test_phase4.py` → `archive/debug_scripts/`

### Config (Organize Configuration)
- `antigravity_config.json` → `config/`
- `claude_config_example.json` → `config/`

### To Create
- `scripts/` directory with startup helpers
- `docs/ARCHITECTURE.md` comprehensive system design
- Updated `.gitignore` excluding logs

### To Remove
- `ollama.log` (already should be gitignored)
- Any `__pycache__` directories

## Cleanup Commands (No Data Loss)

```bash
# Create new directories
mkdir -p archive/historical_plans archive/debug_scripts
mkdir -p scripts config

# Move to archive
mv PLAN.TXT archive/historical_plans/
mv chatsummary.txt archive/historical_plans/
mv debug_bus.py archive/debug_scripts/
mv test_phase4.py archive/debug_scripts/

# Move to config
mv antigravity_config.json config/
mv claude_config_example.json config/

# Remove log file if exists
rm -f ollama.log

# Update .gitignore
echo "ollama.log" >> .gitignore
echo "*.log" >> .gitignore
echo "server_data/" >> .gitignore

# Commit cleanup
git add -A
git commit -m "refactor: reorganize project structure - move obsolete files to archive"
```

## Benefits of This Structure

1. **Cleaner Root** - Only 4 core files in root
2. **Clear Organization** - Everything has a logical home
3. **No Data Loss** - All files preserved in archive/
4. **Better Gitignore** - Logs properly excluded
5. **Easier Navigation** - Related files grouped
6. **Professional** - Matches industry standards
