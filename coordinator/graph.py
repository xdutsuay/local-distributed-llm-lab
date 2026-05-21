from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import operator
from coordinator.planner import Planner
from coordinator.worker_pool import AdaptiveWorkerPool
from coordinator.db import log_event
import time
import asyncio

# Define the state of the graph
class AgentState(TypedDict):
    user_query: str
    plan: List[Dict[str, Any]]
    results: Annotated[List[str], operator.add]
    current_step_index: int
    worker: str # Track last worker ID
    execution_trace: Annotated[List[Dict[str, Any]], operator.add] # Detailed trace of execution

class WorkflowManager:
    def __init__(self, worker_pool: AdaptiveWorkerPool):
        self.planner = Planner()
        # Initialize worker pool for round-robin load balancing
        self.worker_pool = worker_pool
        self.memory = MemorySaver()
        self.workflow = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Nodes
        workflow.add_node("planner", self.plan_node)
        workflow.add_node("executor", self.execute_node)

        # Edges
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "executor")
        
        # Conditional edge to loop execution or finish
        workflow.add_conditional_edges(
            "executor",
            self.should_continue,
            {
                "continue": "executor",
                "end": END
            }
        )

        return workflow.compile(checkpointer=self.memory)

    async def plan_node(self, state: AgentState):
        query = state["user_query"]
        print(f"Planning for: {query}")
        await log_event("plan_start", "coordinator", {"query": query[:200]})

        # --- RAG Integration (Phase 13) ---
        from coordinator.memory import get_vector_store
        memory = get_vector_store()
        context_docs = await asyncio.to_thread(memory.search, query)
        context_str = "\n".join([f"- {doc}" for doc in context_docs])

        if context_str:
            print(f"\U0001f9e0 Retrieved context: {context_str[:100]}...")
            augmented_query = f"{query}\n\nRelevant Context:\n{context_str}"
        else:
            augmented_query = query

        plan = await asyncio.to_thread(self.planner.plan, augmented_query)
        await log_event("plan_done", "coordinator", {"steps": len(plan)})
        return {"plan": plan, "current_step_index": 0}

    async def execute_node(self, state: AgentState):
        plan = state["plan"]
        idx = state["current_step_index"]
        
        if idx < len(plan):
            step = plan[idx]
            print(f"Executing step {idx + 1}: {step['description']}")
            
            # Execute remotely via Ray using worker pool
            # For now, we only support llm_worker type
            prompt = step["payload"].get("prompt", "")
            if not prompt and "query" in step["payload"]:
                 prompt = step["payload"]["query"]
            
            # Handle empty prompt edge case
            if not prompt:
                print(f"⚠️ Warning: Empty prompt for step {idx + 1}")
                prompt = step.get("description", "")
                 
            try:
                start_exec = time.time()
                raw_result = await self.worker_pool.execute(prompt)
                duration = time.time() - start_exec

                # Parse result (local path already returns dict, Ray path may too)
                if isinstance(raw_result, dict):
                    result = raw_result.get("content", "")
                    self.last_worker_id = raw_result.get("node_id", "unknown")
                else:
                    result = str(raw_result)
                    self.last_worker_id = "legacy-worker"
                    
            except Exception as e:
                result = f"Error: {str(e)}"
                self.last_worker_id = "error"
                duration = 0
                await log_event(
                    "execute_error", "coordinator",
                    {"step": idx + 1, "error": str(e), "description": step.get("description", "")}
                )
            
            trace_entry = {
                "step": idx + 1,
                "description": step['description'],
                "node_id": self.last_worker_id,
                "duration": duration,
                "timestamp": time.time()
            }

            return {
                "results": [result], 
                "worker": self.last_worker_id,
                "current_step_index": idx + 1,
                "execution_trace": [trace_entry]
            }
        return {}

    def should_continue(self, state: AgentState):
        if state["current_step_index"] < len(state["plan"]):
            return "continue"
        return "end"

    async def run(self, query: str):
        inputs = {
            "user_query": query,
            "results": [],
            "current_step_index": 0,
            "execution_trace": [],
        }
        # Using a fixed thread_id for this simple phase
        config = {"configurable": {"thread_id": "1"}}
        
        final_state = None
        async for event in self.workflow.astream(inputs, config=config):
            for key, value in event.items():
                print(f"Finished {key}: {value.keys()}")
                final_state = value # Keep tracking the latest state updates
        
        return "Workflow completed."
        
    async def invoke(self, query: str):
        inputs = {
            "user_query": query,
            "results": [],
            "current_step_index": 0,
            "execution_trace": [],
        }
        config = {"configurable": {"thread_id": "1", "checkpoint_ns": "checkpoints"}}
        
        result = await self.workflow.ainvoke(inputs, config=config)
        return result
