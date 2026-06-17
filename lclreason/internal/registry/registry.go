package registry

import (
	"fmt"
	"sync"
	"time"
)

type Node struct {
	ID       string    `json:"id"`
	Address  string    `json:"address"`
	Models   []string  `json:"models"`
	Healthy  bool      `json:"healthy"`
	LastSeen time.Time `json:"last_seen"`
	Load     float64   `json:"load"` // 0.0-1.0
}

type Registry struct {
	mu           sync.RWMutex
	nodes        map[string]*Node
	offlineAfter time.Duration
}

func New(offlineAfter time.Duration) *Registry {
	return &Registry{
		nodes:        make(map[string]*Node),
		offlineAfter: offlineAfter,
	}
}

func (r *Registry) Register(n *Node) {
	r.mu.Lock()
	defer r.mu.Unlock()
	n.LastSeen = time.Now()
	n.Healthy = true
	r.nodes[n.ID] = n
}

func (r *Registry) Heartbeat(id string, load float64) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	n, ok := r.nodes[id]
	if !ok {
		return fmt.Errorf("node %q not registered", id)
	}
	n.LastSeen = time.Now()
	n.Healthy = true
	n.Load = load
	return nil
}

func (r *Registry) Deregister(id string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	delete(r.nodes, id)
}

// Healthy returns all nodes that have sent a heartbeat recently.
func (r *Registry) Healthy() []*Node {
	r.mu.RLock()
	defer r.mu.RUnlock()
	cutoff := time.Now().Add(-r.offlineAfter)
	var out []*Node
	for _, n := range r.nodes {
		if n.LastSeen.After(cutoff) {
			out = append(out, n)
		}
	}
	return out
}

func (r *Registry) All() []*Node {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]*Node, 0, len(r.nodes))
	for _, n := range r.nodes {
		out = append(out, n)
	}
	return out
}

// Sweep marks stale nodes offline; called periodically.
func (r *Registry) Sweep() {
	r.mu.Lock()
	defer r.mu.Unlock()
	cutoff := time.Now().Add(-r.offlineAfter)
	for _, n := range r.nodes {
		n.Healthy = n.LastSeen.After(cutoff)
	}
}
