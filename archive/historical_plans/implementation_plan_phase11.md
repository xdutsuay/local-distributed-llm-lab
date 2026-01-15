# Phase 11 Implementation Plan: Mobile Mesh Integration

Enable distributed tool execution, caching, and mobile node participation in the LLM cluster.

## User Review Required

> [!IMPORTANT]
> This phase introduces a **tool execution framework** that allows workers to call external tools (web search, calculations, browser automation). The planner will identify when tools are needed and route tasks to capable workers.

> [!IMPORTANT]
> **Caching strategy**: Using Ray's distributed object store for LLM response caching. Cache keys are generated from `hash(prompt + model + parameters)`. This avoids redundant API calls and reduces latency.

> [!WARNING]
> Mobile nodes will have limited capabilities (no local LLM inference). They can execute tools and serve as cache replicas but cannot run heavy models.

## Proposed Changes

### Tool Execution Component

#### [NEW] [tools/base.py](file:///Users/nehatiwari/localcode/LLMLAB/coordinator/tools/base.py)

**Purpose:** Define abstract base class for all tools

**Features:**
- `Tool` abstract class with `execute()` method  
- Input/output schema validation
- Capability registration
- Error handling

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        pass
```

---

#### [NEW] [tools/registry.py](file:///Users/nehatiwari/localcode/LLMLAB/coordinator/tools/registry.py)

**Purpose:** Manage available tools and route tool calls

**Features:**
- Register tools dynamically
- Query tools by capability
- Route tool execution to appropriate workers
- Track tool usage statistics

---

#### [NEW] [tools/builtin_tools.py](file:///Users/nehatiwari/localcode/LLMLAB/coordinator/tools/builtin_tools.py)

**Purpose:** Provide example tool implementations

**Tools:**
- `CalculatorTool` - Basic arithmetic
- `WebSearchTool` - Web search (mock or real API)
- `BrowserTool` - Headless browser automation

---

### Caching Component

#### [NEW] [coordinator/cache_manager.py](file:///Users/nehatiwari/localcode/LLMLAB/coordinator/cache_manager.py)

**Purpose:** Distributed caching for LLM responses

**Features:**
- Cache key generation from prompt hash
- Ray object store integration
- TTL-based expiration (default: 1 hour)
- Cache hit/miss statistics
- Eviction policy (LRU)

**Key methods:**
- `get(prompt, model) -> Optional[str]` - Retrieve cached response
- `put(prompt, model, response, ttl) -> None` - Store response
- `get_stats() -> Dict` - Cache statistics

---

#### [MODIFY] [worker.py](file:///Users/nehatiwari/localcode/LLMLAB/coordinator/worker.py)

**Changes:**
1. Import `CacheManager`
2. Check cache before calling Ollama
3. Store successful responses in cache
4. Add cache statistics to heartbeat

**Specific modifications:**
- Lines 66-100: Wrap `generate()` with cache lookup/store
- Add cache hit counter to worker metrics

---

#### [MODIFY] [graph.py](file:///Users/nehatiwari/localcode/LLMLAB/coordinator/graph.py)

**Changes:**
1. Initialize `CacheManager` in `WorkflowManager`
2. Pass cache manager to worker pool
3. Track cache hits in execution trace

---

### Mobile Node Enhancement

#### [MODIFY] [index.html](file:///Users/nehatiwari/localcode/LLMLAB/frontend/index.html)

**Changes:**
1. Add task assignment listener via WebSocket
2. Implement lightweight tool execution in browser
3. Send task results back to coordinator
4. Display current task in UI

**New WebSocket messages:**
- `task_assignment` - Coordinator assigns task to mobile node
- `task_result` - Mobile node returns result
- `cache_sync` - Sync cache entries to mobile

---

#### [NEW] [frontend/mobile_worker.js](file:///Users/nehatiwari/localcode/LLMLAB/frontend/mobile_worker.js)

**Purpose:** Client-side task execution engine

**Features:**
- Execute browser-based tools (fetch API, localStorage)
- Maintain local cache replica
- Report capabilities to coordinator

---

#### [MODIFY] [main.py](file:///Users/nehatiwari/localcode/LLMLAB/coordinator/main.py)

**Changes:**
1. Add `/ws/task` WebSocket for task distribution
2. Route tool-only tasks to mobile nodes
3. Implement task result aggregation

---

### Replication Component

#### [NEW] [coordinator/replicator.py](file:///Users/nehatiwari/localcode/LLMLAB/coordinator/replicator.py)

**Purpose:** Replicate cache entries across nodes

**Features:**
- Push critical cache entries to N replicas (N=2)
- Track replica locations
- Handle node failure gracefully
- Prioritize frequently accessed entries

**Key methods:**
- `replicate(key, value, num_replicas) -> List[str]` - Replicate to N nodes
- `get_replicas(key) -> List[str]` - Find replica node IDs
- `sync_to_node(node_id, entries) -> None` - Sync cache to specific node

---

### Testing Component

#### [NEW] [tests/test_tools.py](file:///Users/nehatiwari/localcode/LLMLAB/tests/test_tools.py)

**Test cases:**
- Tool registration and discovery
- Tool execution with workers
- Tool error handling
- Planner identifies tool requirements

---

#### [NEW] [tests/test_caching.py](file:///Users/nehatiwari/localcode/LLMLAB/tests/test_caching.py)

**Test cases:**
- Cache hit/miss behavior
- TTL expiration
- Cache key generation
- Distributed cache access

---

#### [NEW] [tests/test_mobile.py](file:///Users/nehatiwari/localcode/LLMLAB/tests/test_mobile.py)

**Test cases:**
- Mobile node registration
- Task assignment to mobile
- Mobile tool execution
- Cache sync to mobile

---

## Verification Plan

### Automated Tests

```bash
# Tool execution tests
pytest tests/test_tools.py -v

# Caching tests  
pytest tests/test_caching.py -v

# Mobile integration tests
pytest tests/test_mobile.py -v

# Full suite
pytest tests/ --ignore=tests/test_mcp.py -k "not skip"
```

Expected: All new tests pass, existing tests remain passing

### Manual Verification

**Test tool execution:**
1. Start coordinator
2. Send query: "What is 25 * 67?" (should route to CalculatorTool)
3. Verify tool result in response
4. Check `/api/tasks` shows tool attribution

**Test caching:**
1. Send query: "Tell me a joke"
2. Note response time
3. Send same query again
4. Verify response time is <100ms (cache hit)
5. Check cache stats in dashboard

**Test mobile node:**
1. Open mobile PWA on phone
2. Verify node appears in `/llmlab` dashboard
3. Send task that requires browser tool
4. Verify mobile node executes task
5. Check mobile logs for task assignment

**Test replication:**
1. Start coordinator with 3 workers
2. Cache entry A on worker 1
3. Verify entry replicates to 2 other workers
4. Stop worker 1
5. Verify entry still accessible from replicas

---

## Architecture Evolution

### Before Phase 11
```
User → Planner → Worker Pool → Ollama → Response
```

### After Phase 11
```
                            ┌─→ ToolWorker (Calculator)
User → Planner → Router ────┼─→ LLMWorker (cached/uncached)
                            └─→ MobileWorker (Browser tools)
                                      ↓
                              Distributed Cache
                                (replicated)
```

**Benefits:**
- **Tool ecosystem** for extended functionality
- **Cache reduces costs** by avoiding duplicate LLM calls
- **Mobile participation** leverages idle phone compute
- **Fault tolerance** through replication

---

## Rollout Strategy

### Phase 11.1: Tools Foundation (Priority: High)
- Implement tool base class and registry
- Add 3 example tools
- Integrate with planner

### Phase 11.2: Caching (Priority: High)  
- Implement CacheManager
- Integrate with workers
- Add cache statistics

### Phase 11.3: Mobile Enhancement (Priority: Medium)
- Update PWA with task execution
- Test mobile tool execution

### Phase 11.4: Replication (Priority: Low)
- Implement replication strategy
- Test fault tolerance

This staged approach allows incremental value delivery while managing complexity.
