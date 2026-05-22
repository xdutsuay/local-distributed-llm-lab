"""
AdaptiveWorkerPool — @ray_required adaptive dispatch
=====================================================

Single node  → task executed directly in the coordinator process.
              No Ray IPC, no forked subprocesses, no serialisation overhead.
              AirLLM / torch / mlx work cleanly in this path.

Multi-node   → task dispatched to a Ray remote actor via round-robin,
              exactly as before when additional LLM-capable nodes exist.

The switch is controlled by active LLM-capable node count, not every
connected browser/mobile node.
"""
import asyncio
import os
import threading
import uuid
from typing import Any, Dict, Optional

import ray

from coordinator.worker import LLMWorker
import re

def inject_microgpt_context(prompt: str) -> str:
    """
    Replicates the microgpt structure (previously in the browser) directly on the worker node.
    Extracts summary, keywords, and clauses to provide structured <BOS> metadata.
    """
    stopwords = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
        "i", "if", "in", "into", "is", "it", "its", "me", "of", "on", "or",
        "our", "should", "that", "the", "their", "then", "this", "to", "we",
        "what", "when", "where", "which", "with", "you", "your",
    }
    
    words = re.findall(r"[a-z0-9']+", prompt.lower())
    keywords = list(dict.fromkeys([w for w in words if len(w) > 3 and w not in stopwords]))[:8]
    
    clauses = [p.strip() for p in re.split(r'\?|\.|!|,|\band\b|\bthen\b', prompt, flags=re.IGNORECASE) if p.strip()][:4]
    summary = clauses[0] if clauses else prompt[:120]
    
    context = (
        "<BOS>\n"
        f"MicroGPT Context:\n"
        f"Summary: {summary}\n"
        f"Keywords: {', '.join(keywords)}\n"
        f"Clauses: {len(clauses)}\n"
        "</BOS>\n\n"
    )
    return context + prompt


# ---------------------------------------------------------------------------
# Local (in-process) worker — identical interface to the Ray actor
# ---------------------------------------------------------------------------

class LocalLLMWorker:
    """
    Non-Ray, in-process worker.  Same `generate()` interface as LLMWorker
    but called directly — no serialisation, no forked subprocess.
    """

    def __init__(self):
        import os
        self.node_id = "local-worker"
        self.backend = os.getenv("INFERENCE_BACKEND", "ollama").lower()
        self.model_name = os.getenv("OLLAMA_MODEL", "") or self._detect_model()
        self._airllm_model: Optional[Any] = None
        self.generated_bytes = 0
        self.last_task = "Idle"

        if self.backend == "airllm":
            self._init_airllm()

    def _detect_model(self) -> str:
        from coordinator.worker import detect_available_models
        detected = detect_available_models()
        return detected if detected else "llama3.2"

    def _init_airllm(self):
        try:
            from airllm import AutoModel
            print(f"🚀 [LocalWorker] AirLLM loading '{self.model_name}'...")
            self._airllm_model = AutoModel.from_pretrained(self.model_name)
            print(f"✅ [LocalWorker] AirLLM ready.")
        except ImportError:
            print("⚠️ airllm not installed — falling back to Ollama. `pip install airllm`")
            self.backend = "ollama"
        except Exception as e:
            print(f"⚠️ AirLLM init error ({e}) — falling back to Ollama.")
            self.backend = "ollama"

    async def generate(self, prompt: str) -> Dict[str, Any]:
        import time
        from coordinator.cache_manager import get_cache_manager
        cache = get_cache_manager()

        cached = cache.get(prompt, self.model_name)
        if cached:
            return {"content": cached, "node_id": self.node_id,
                    "model": self.model_name, "timestamp": time.time(), "cached": True}

        self.last_task = f"Processing: {prompt[:20]}..."
        result = self._run_inference(prompt)
        cache.put(prompt, self.model_name, result["content"])
        self.last_task = "Idle"
        return result

    def generate_sync(self, prompt: str) -> Dict[str, Any]:
        """Fully synchronous version — safe to call from LangGraph sync nodes."""
        import time
        from coordinator.cache_manager import get_cache_manager
        cache = get_cache_manager()

        cached = cache.get(prompt, self.model_name)
        if cached:
            return {"content": cached, "node_id": self.node_id,
                    "model": self.model_name, "timestamp": time.time(), "cached": True}

        self.last_task = f"Processing: {prompt[:20]}..."
        result = self._run_inference(prompt)
        cache.put(prompt, self.model_name, result["content"])
        self.last_task = "Idle"
        return result

    def _run_inference(self, prompt: str) -> Dict[str, Any]:
        """Shared sync inference — called by both generate() and generate_sync()."""
        import time

        # --- AirLLM path ---
        if self.backend == "airllm" and self._airllm_model is not None:
            try:
                input_text = f"<s>[INST] {prompt} [/INST]"
                tokens = self._airllm_model.tokenizer(
                    input_text, return_tensors="pt", truncation=True, max_length=512
                )
                out = self._airllm_model.generate(
                    tokens["input_ids"],
                    attention_mask=tokens.get("attention_mask"),
                    max_new_tokens=256,
                    do_sample=False,
                )
                resp = self._airllm_model.tokenizer.decode(
                    out[0][tokens["input_ids"].shape[1]:], skip_special_tokens=True
                )
                self.generated_bytes += len(resp.encode())
                return {"content": resp, "node_id": self.node_id,
                        "model": f"airllm:{self.model_name}",
                        "timestamp": time.time(), "cached": False}
            except Exception as e:
                print(f"⚠️ AirLLM generate error ({e}) — falling back to Ollama.")

        # --- LM Studio path ---
        if self.backend == "lmstudio":
            try:
                import requests
                api_base = "http://127.0.0.1:1234/v1"
                response = requests.post(
                    f"{api_base}/chat/completions",
                    json={
                        "model": self.model_name or "local-model",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7
                    },
                    timeout=60
                )
                if response.status_code == 200:
                    resp = response.json()['choices'][0]['message']['content']
                    self.generated_bytes += len(resp.encode())
                    return {"content": resp, "node_id": self.node_id,
                            "model": f"lmstudio:{self.model_name}",
                            "timestamp": time.time(), "cached": False}
                else:
                    print(f"⚠️ LM Studio API Error: {response.text}")
            except Exception as e:
                print(f"⚠️ LM Studio generate error ({e}) — falling back to Ollama.")

        # --- Ollama path (default / fallback) ---
        import ollama
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                keep_alive="60m",
            )
            resp = response["message"]["content"]
            self.generated_bytes += len(resp.encode())
            return {"content": resp, "node_id": self.node_id,
                    "model": self.model_name, "timestamp": time.time(), "cached": False}
        except Exception as e:
            error_str = str(e)
            if "not found" in error_str or "pull" in error_str:
                try:
                    ollama.pull(self.model_name)
                    response = ollama.chat(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    resp = response["message"]["content"]
                    self.generated_bytes += len(resp.encode())
                    return {"content": resp, "node_id": self.node_id,
                            "model": self.model_name, "timestamp": time.time(), "cached": False}
                except Exception as pull_error:
                    print(f"Local Pull failed: {pull_error}")
            
            print(f"Local Ollama inference failed: {e}. Falling back to mock.")
            resp = f"[Mock] Response from {self.model_name} (Node: {self.node_id}) to prompt: '{prompt}'"
            self.generated_bytes += len(resp.encode())
            return {"content": resp, "node_id": self.node_id,
                    "model": self.model_name, "timestamp": time.time(), "cached": False}


# ---------------------------------------------------------------------------
# @ray_required decorator
# ---------------------------------------------------------------------------

def ray_required(method):
    """
    Method decorator for WorkerPool.  At call time:
      - node count > 1  →  original Ray-based method
      - node count == 1 →  local fast path (self._local_execute)
    """
    async def wrapper(self: "AdaptiveWorkerPool", prompt: str):
        if _registry_llm_count(self) > 1:
            return await method(self, prompt)      # Ray path
        return await self._local_execute(prompt)
    wrapper.__name__ = method.__name__
    return wrapper


def _registry_llm_count(pool: Any) -> int:
    if os.getenv("FORCE_LOCAL_WORKER") == "1":
        return 1
    if hasattr(pool, "_active_llm_node_count"):
        return pool._active_llm_node_count()
    registry = getattr(pool, "_registry", None)
    if registry is None:
        return 1
    if hasattr(registry, "active_llm_node_count"):
        return registry.active_llm_node_count()
    return registry.active_node_count()


# ---------------------------------------------------------------------------
# AdaptiveWorkerPool
# ---------------------------------------------------------------------------

class AdaptiveWorkerPool:
    """
    Replaces the old WorkerPool.

    Single-node:  one LocalLLMWorker (in-process, no Ray)
    Multi-node:   pool of @ray.remote LLMWorker actors (same as before)
    """

    def __init__(self, num_workers: int = 3, registry=None):
        self._registry = registry   # NodeRegistry — set after startup
        self._num_workers = num_workers
        self._lock = threading.Lock()
        self._rr_index = 0

        # Local (in-process) worker — always created, zero overhead on idle
        self._local_worker = LocalLLMWorker()

        # Ray actors — created lazily when first needed on multi-node
        self._ray_workers = []
        self._ray_ready = False

        print("✅ AdaptiveWorkerPool ready (single-node fast path active)")

    # ------------------------------------------------------------------
    # Public API  — uniform regardless of mode
    # ------------------------------------------------------------------

    @ray_required
    async def execute(self, prompt: str) -> Dict[str, Any]:
        """Ray path — round-robin across remote actors."""
        worker = self._get_next_ray_worker()
        enhanced_prompt = inject_microgpt_context(prompt)
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(
            None, lambda: ray.get(worker.generate.remote(enhanced_prompt))
        )
        if isinstance(raw, dict):
            return raw
        return {"content": str(raw), "node_id": "unknown",
                "model": "unknown", "timestamp": 0, "cached": False}

    async def _local_execute(self, prompt: str) -> Dict[str, Any]:
        """Local path — direct async call, no Ray."""
        enhanced_prompt = inject_microgpt_context(prompt)
        return await self._local_worker.generate(enhanced_prompt)

    def execute_sync(self, prompt: str) -> Dict[str, Any]:
        """
        Synchronous bridge — for use inside LangGraph sync nodes (plain def).

        Single-node: runs LocalLLMWorker.generate() via a dedicated background
                     asyncio loop (avoids 'no running loop' errors when called
                     from a thread that has no event loop).
        Multi-node:  calls ray.get() which is already blocking.
        """
        enhanced_prompt = inject_microgpt_context(prompt)
        if self._active_llm_node_count() > 1:
            # Ray path — blocking ray.get is fine from sync context
            worker = self._get_next_ray_worker()
            raw = ray.get(worker.generate.remote(enhanced_prompt))
            if isinstance(raw, dict):
                return raw
            return {"content": str(raw), "node_id": "unknown",
                    "model": "unknown", "timestamp": 0, "cached": False}

        # Local path — call the sync version directly (no nested loop issues)
        return self._local_worker.generate_sync(enhanced_prompt)

    def execute_local_sync(self, prompt: str) -> Dict[str, Any]:
        """Force execution on the local worker regardless of connected node count."""
        enhanced_prompt = inject_microgpt_context(prompt)
        return self._local_worker.generate_sync(enhanced_prompt)

    # ------------------------------------------------------------------
    # Ray actor management (lazy init)
    # ------------------------------------------------------------------

    def _ensure_ray_workers(self):
        if self._ray_ready:
            return
        print(f"🔧 Initialising {self._num_workers} Ray workers for multi-node mode...")
        for i in range(self._num_workers):
            try:
                wid = f"worker-{str(uuid.uuid4())[:8]}"
                w = LLMWorker.options(name=wid).remote(node_id=wid)
                self._ray_workers.append(w)
                print(f"  ✓ Ray worker {i+1}/{self._num_workers} ({wid})")
            except Exception as e:
                print(f"  ✗ Ray worker {i+1} failed: {e}")
        self._ray_ready = True

    def _get_next_ray_worker(self):
        self._ensure_ray_workers()
        if not self._ray_workers:
            raise RuntimeError("No Ray workers available")
        with self._lock:
            w = self._ray_workers[self._rr_index % len(self._ray_workers)]
            self._rr_index += 1
            return w

    # ------------------------------------------------------------------
    # Legacy compatibility shims (used by graph.py / tests)
    # ------------------------------------------------------------------

    def get_next_worker(self):
        """Return the local worker (single-node) or a Ray actor handle (multi-node)."""
        if self._registry and self._registry.active_node_count() > 1:
            return self._get_next_ray_worker()
        return self._local_worker

    def set_registry(self, registry) -> None:
        """Inject the NodeRegistry after startup (avoids circular import)."""
        self._registry = registry

    def get_pool_size(self) -> int:
        return len(self._ray_workers) or 1

    def is_local_mode(self) -> bool:
        return self._active_llm_node_count() <= 1

    def _active_llm_node_count(self) -> int:
        if os.getenv("FORCE_LOCAL_WORKER") == "1":
            return 1
        if not self._registry:
            return 1
        if hasattr(self._registry, "active_llm_node_count"):
            return self._registry.active_llm_node_count()
        return self._registry.active_node_count()
