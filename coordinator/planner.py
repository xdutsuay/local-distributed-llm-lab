import json
from typing import List, Dict, Any
import ollama

class Planner:
    def __init__(self, model_name: str = "llama3.2"):
        self.model_name = model_name

    def plan(self, user_query: str) -> List[Dict[str, Any]]:
        """
        Decomposes a user query into a list of execution steps.
        """
        system_prompt = """
        You are a task planner for a distributed LLM system.
        Your goal is to decompose a user request into a sequence of steps.
        Return ONLY a JSON array of objects, where each object has:
        - "step_id": int
        - "description": str
        - "worker_type": str (e.g., "llm_worker", "tool_worker")
        - "payload": dict (arguments for the step)
        
        Example:
        [
            {"step_id": 1, "description": "Summarize text", "worker_type": "llm_worker", "payload": {"prompt": "Summarize this..."}}
        ]
        """
        
        try:
            response = ollama.chat(model=self.model_name, messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_query},
            ])
            
            content = response['message']['content']
            # Simple cleanup to ensure JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            return json.loads(content.strip())
            
        except Exception as e:
            print(f"Error generating plan: {e}")
            # Fallback for simple queries or errors
            return [{
                "step_id": 1,
                "description": "Execute user query directly",
                "worker_type": "llm_worker",
                "payload": {"prompt": user_query}
            }]
