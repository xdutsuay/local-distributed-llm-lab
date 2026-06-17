package dispatch

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sort"
	"time"

	"github.com/xdutsuay/lclreason/internal/registry"
)

// OllamaRequest maps to Ollama's /api/generate endpoint.
type OllamaRequest struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
	Stream bool   `json:"stream"`
}

type OllamaResponse struct {
	Response string `json:"response"`
}

type Dispatcher struct {
	reg    *registry.Registry
	client *http.Client
}

func New(reg *registry.Registry) *Dispatcher {
	return &Dispatcher{
		reg:    reg,
		client: &http.Client{Timeout: 120 * time.Second},
	}
}

// Invoke satisfies chain.Invoker — picks the best node and calls it.
func (d *Dispatcher) Invoke(ctx context.Context, model, prompt string) (string, error) {
	node, err := d.pick(model)
	if err != nil {
		return "", err
	}
	return d.forward(ctx, node, model, prompt)
}

func (d *Dispatcher) pick(model string) (*registry.Node, error) {
	nodes := d.reg.Healthy()
	if len(nodes) == 0 {
		return nil, fmt.Errorf("no healthy nodes registered")
	}

	// Filter by model if possible; fall back to all healthy nodes.
	var candidates []*registry.Node
	for _, n := range nodes {
		for _, m := range n.Models {
			if m == model || model == "" {
				candidates = append(candidates, n)
				break
			}
		}
	}
	if len(candidates) == 0 {
		candidates = nodes
	}

	// Sort by load ascending, pick lowest.
	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].Load < candidates[j].Load
	})
	return candidates[0], nil
}

func (d *Dispatcher) forward(ctx context.Context, node *registry.Node, model, prompt string) (string, error) {
	body, _ := json.Marshal(OllamaRequest{Model: model, Prompt: prompt, Stream: false})
	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		"http://"+node.Address+"/api/generate", bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := d.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("node %s: %w", node.ID, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("node %s returned %d: %s", node.ID, resp.StatusCode, b)
	}

	var out OllamaResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return "", fmt.Errorf("decode response: %w", err)
	}
	return out.Response, nil
}
