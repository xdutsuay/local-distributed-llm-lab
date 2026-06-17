package api

import (
	"context"
	"encoding/json"
	"net/http"
	"strconv"
	"time"

	"github.com/xdutsuay/lclreason/internal/cache"
	"github.com/xdutsuay/lclreason/internal/chain"
	"github.com/xdutsuay/lclreason/internal/dispatch"
	"github.com/xdutsuay/lclreason/internal/registry"
	"github.com/xdutsuay/lclreason/internal/store"
)

type Handlers struct {
	reg   *registry.Registry
	dis   *dispatch.Dispatcher
	eng   *chain.Engine
	cache *cache.Cache
	store *store.Store
}

// ---- node management ----

func (h *Handlers) RegisterNode(w http.ResponseWriter, r *http.Request) {
	var n registry.Node
	if err := json.NewDecoder(r.Body).Decode(&n); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	h.reg.Register(&n)
	_ = h.store.Log(r.Context(), store.Event{Kind: "node_register", NodeID: n.ID})
	writeJSON(w, http.StatusCreated, n)
}

func (h *Handlers) Heartbeat(w http.ResponseWriter, r *http.Request) {
	var body struct {
		ID   string  `json:"id"`
		Load float64 `json:"load"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	if err := h.reg.Heartbeat(body.ID, body.Load); err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (h *Handlers) DeregisterNode(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	h.reg.Deregister(id)
	_ = h.store.Log(r.Context(), store.Event{Kind: "node_deregister", NodeID: id})
	w.WriteHeader(http.StatusNoContent)
}

func (h *Handlers) ListNodes(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, h.reg.All())
}

// ---- OpenAI-compatible chat ----

type ChatRequest struct {
	Model    string        `json:"model"`
	Messages []ChatMessage `json:"messages"`
	Chain    string        `json:"chain"` // lclreason extension
	Stream   bool          `json:"stream"`
}

type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ChatResponse struct {
	ID      string   `json:"id"`
	Object  string   `json:"object"`
	Created int64    `json:"created"`
	Model   string   `json:"model"`
	Choices []Choice `json:"choices"`
	Usage   Usage    `json:"usage"`
}

type Choice struct {
	Index   int         `json:"index"`
	Message ChatMessage `json:"message"`
}

type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

func (h *Handlers) ChatCompletions(w http.ResponseWriter, r *http.Request) {
	var req ChatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Flatten messages into a single prompt.
	prompt := flattenMessages(req.Messages)
	model := req.Model
	if model == "" {
		model = "llama3"
	}

	// Cache check.
	if hit, ok := h.cache.Get(model, prompt); ok {
		writeJSON(w, http.StatusOK, buildResponse(model, hit))
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 120*time.Second)
	defer cancel()

	start := time.Now()
	result, err := h.eng.Run(ctx, req.Chain, prompt, model)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	elapsed := time.Since(start)

	h.cache.Set(model, prompt, result.Output)
	_ = h.store.Log(r.Context(), store.Event{
		Kind:       "chat",
		Model:      model,
		Prompt:     prompt,
		Response:   result.Output,
		DurationMs: elapsed.Milliseconds(),
	})

	writeJSON(w, http.StatusOK, buildResponse(model, result.Output))
}

func (h *Handlers) ListModels(w http.ResponseWriter, r *http.Request) {
	type modelObj struct {
		ID     string `json:"id"`
		Object string `json:"object"`
	}
	seen := map[string]bool{}
	var models []modelObj
	for _, n := range h.reg.Healthy() {
		for _, m := range n.Models {
			if !seen[m] {
				seen[m] = true
				models = append(models, modelObj{ID: m, Object: "model"})
			}
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{"object": "list", "data": models})
}

// ---- events / observability ----

func (h *Handlers) ListEvents(w http.ResponseWriter, r *http.Request) {
	limit := 50
	if s := r.URL.Query().Get("limit"); s != "" {
		if n, err := strconv.Atoi(s); err == nil && n > 0 {
			limit = n
		}
	}
	events, err := h.store.Recent(r.Context(), limit)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	writeJSON(w, http.StatusOK, events)
}

// ---- health ----

func (h *Handlers) Health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"status":       "ok",
		"nodes_total":  len(h.reg.All()),
		"nodes_healthy": len(h.reg.Healthy()),
		"cache_size":   h.cache.Len(),
	})
}

// ---- dashboard (embedded HTML) ----

func (h *Handlers) Dashboard(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	http.ServeFile(w, r, "web/dashboard.html")
}

// ---- helpers ----

func flattenMessages(msgs []ChatMessage) string {
	var out string
	for _, m := range msgs {
		out += m.Role + ": " + m.Content + "\n"
	}
	return out
}

func buildResponse(model, content string) ChatResponse {
	return ChatResponse{
		ID:      "chatcmpl-local",
		Object:  "chat.completion",
		Created: time.Now().Unix(),
		Model:   model,
		Choices: []Choice{{
			Index:   0,
			Message: ChatMessage{Role: "assistant", Content: content},
		}},
	}
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}
