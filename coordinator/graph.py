from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import operator
import ray
from coordinator.planner import Planner
from coordinator.worker import LLMWorker
import time

# Define the state of the graph
class AgentState(TypedDict):
    user_query: str
    plan: List[Dict[str, Any]]
    results: Annotated[List[str], operator.add]
    current_step_index: int
    worker: str # Track last worker ID
    execution_trace: Annotated[List[Dict[str, Any]], operator.add] # Detailed trace of execution

class WorkflowManager:
    def __init__(self):
        self.planner = Planner()
        # Initialize Ray worker (in real app, use a pool or router)
        self.worker = LLMWorker.remote() 
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

    def plan_node(self, state: AgentState):
        query = state["user_query"]
        print(f"Planning for: {query}")
        plan = self.planner.plan(query)
        return {"plan": plan, "current_step_index": 0}

    def execute_node(self, state: AgentState):
        plan = state["plan"]
        idx = state["current_step_index"]
        
        if idx < len(plan):
            step = plan[idx]
            print(f"Executing step {idx + 1}: {step['description']}")
            
            # Execute remotely via Ray
            # For now, we only support llm_worker type
            prompt = step["payload"].get("prompt", "")
            if not prompt and "query" in step["payload"]:
                 prompt = step["payload"]["query"]
                 
            try:
                start_exec = time.time()
                response_ref = self.worker.generate.remote(prompt)
                raw_result = ray.get(response_ref)
                duration = time.time() - start_exec
                
                # Parse Result
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
        inputs = {"user_query": query, "results": [], "current_step_index": 0, "execution_trace": []}
        # Using a fixed thread_id for this simple phase
        config = {"configurable": {"thread_id": "1"}}
        
        final_state = None
        for event in self.workflow.stream(inputs, config=config):
            for key, value in event.items():
                print(f"Finished {key}: {value.keys()}")
                final_state = value # Keep tracking the latest state updates
        
        return "Workflow completed."
        
    async def invoke(self, query: str):
        inputs = {"user_query": query, "results": [], "current_step_index": 0, "execution_trace": []}
        config = {"configurable": {"thread_id": "1", "checkpoint_ns": "checkpoints"}}
        
        result = await self.workflow.ainvoke(inputs, config=config)
        return result
