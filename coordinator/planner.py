import json
import os
from typing import List, Dict, Any
import ollama
from coordinator.worker import detect_available_models
from coordinator.profiler import profile

class Planner:
    def __init__(self, model_name: str = None):
        # Fallback chain: explicit param → env var → auto-detect → default
        if model_name:
            self.model_name = model_name
        elif os.getenv("OLLAMA_MODEL"):
            self.model_name = os.getenv("OLLAMA_MODEL")
        else:
            detected = detect_available_models()
            self.model_name = detected if detected else "qwen2.5-coder"
            if not detected:
                print(f"ℹ️ Planner using default model: {self.model_name}")
        
        print(f"📋 Planner initialized with model: {self.model_name}")

    @profile
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
            ], options={'temperature': 0.1})
            
            content = response['message']['content'].strip()
            print(f"🔍 Raw Planner Output: {content[:100]}...")
            
            # Robust cleanup
            if "```" in content:
                import re
                match = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL)
                if match:
                    content = match.group(1).strip()
                else:
                    # Fallback if regex fails but backticks exist
                    content = content.replace("```json", "").replace("```", "").strip()
            
            return json.loads(content)
            
        except Exception as e:
            print(f"Error generating plan: {e}")
            # Fallback for simple queries or errors
            return [{
                "step_id": 1,
                "description": "Execute user query directly",
                "worker_type": "llm_worker",
                "payload": {"prompt": user_query}
            }]
