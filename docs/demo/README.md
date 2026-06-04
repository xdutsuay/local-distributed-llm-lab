# LLMLAB demo video

## Latest recording

**File:** [`llmlab-demo.mp4`](llmlab-demo.mp4) (screen capture via ffmpeg)

**Recorded flow:**
1. Dashboard at http://localhost:8000/llmlab — LM Studio provider
2. Chat UI — prompt: "What is 2+2? Reply with the number only."
3. LangGraph plan + response (Gemma / local-worker)
4. Task History tab

## Prerequisites

- Coordinator running: `./scripts/start_coordinator.sh`
- LM Studio with Gemma on http://127.0.0.1:1234
- macOS **Screen Recording** permission for Terminal/Cursor (System Settings → Privacy & Security)
- ffmpeg (already on Homebrew: `brew install ffmpeg`)

## Re-record

```bash
# Terminal 1 — coordinator (if not running)
INFERENCE_BACKEND=lmstudio LMSTUDIO_API_BASE=http://127.0.0.1:1234/v1 ./scripts/start_coordinator.sh

# Terminal 2 — start capture (screen device 1 = "Capture screen 0")
LLMLAB_AV_SCREEN_DEVICE=1 ./scripts/record_demo.sh start 240

# Drive UI in browser, then:
./scripts/record_demo.sh stop
```

List capture devices: `./scripts/record_demo.sh devices`
