# Issue 001: Planner Prompt Mismatch & Single-Node Routing

**Status**: Open  
**Priority**: High  
**Reported**: 2026-01-13  

## Description
The user observed a discrepancy where the Chat UI displays a response claiming "no question was provided", despite the system logs clearly showing a valid prompt ("how can i use notebook lm...").

Additionally, the user questioned why the task composition showed ~100% processing by a single node (`worker-2011...`) when two workers were active in the cluster.

### Evidence
**Log Snippet:**
```json
{
  "id": "f3d5f8ae...",
  "prompt": "how can i use notebook lm to read pdfs...",
  "route_details": [
    { "step": 1, "description": "Execute user query directly", "node_id": "worker-201..." },
    { "step": 1, "description": "Execute user query directly", "node_id": "worker-201..." }
  ],
  "composition": {
    "worker-201105832418322": 99.15
  }
}
```

**Screenshots:**
![Chat Mismatch](file:///Users/nehatiwari/.gemini/antigravity/brain/613b969a-8db4-40da-b134-15b83251b668/uploaded_image_1_1768322648869.jpg)
*Figure 1: Model responds "It seems like you didn't provide a question" despite valid prompt.*

## Analysis
1.  **Prompt Passing Failure**: The planner likely successfully decomposed the task (as seen in `route_details`), but when invoking the `worker.generate` for the specific step, the `payload` or `prompt` variable might have been empty or malformed.
    *   *Suspect*: `coordinator/graph.py` -> `execute_node` logic where it extracts `step["payload"]["prompt"]`.
2.  **Duplicate Steps**: The log shows "Step 1" executing twice with the same description. This implies a loop or race condition in the `WorkflowManager`.
3.  **Routing Imbalance**: All steps went to one worker. This confirms that while the *cluster* has 2 nodes, the *scheduler* is not round-robin load balancing. It's likely picking the same remote actor each time or `worker.py` is effectively a singleton per machine.

## Action Plan (Next Session)
- [ ] Debug `graph.py` payload extraction to ensure prompt is passed to worker.
- [ ] Investigate `LangGraph` stream loop to fix duplicate step execution.
- [ ] Implement explicit Round-Robin or Load-Aware routing in `WorkflowManager` to utilize both nodes.
