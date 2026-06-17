package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"runtime"

	"github.com/xdutsuay/lclreason/internal/config"
	"github.com/xdutsuay/lclreason/internal/registry"
)

type worker struct {
	cfg    *config.Config
	client *http.Client
	id     string
}

func (w *worker) register() error {
	hostname, _ := os.Hostname()
	w.id = fmt.Sprintf("%s-%d", hostname, w.cfg.Port)

	n := registry.Node{
		ID:      w.id,
		Address: fmt.Sprintf("%s:%d", hostname, w.cfg.Port),
		Models:  []string{"llama3"}, // TODO: query local Ollama for actual models
		Load:    0,
	}
	return w.post("/v1/nodes/register", n)
}

func (w *worker) heartbeat() error {
	var ms runtime.MemStats
	runtime.ReadMemStats(&ms)
	load := float64(ms.Alloc) / float64(ms.Sys)
	return w.post("/v1/nodes/heartbeat", map[string]any{"id": w.id, "load": load})
}

func (w *worker) deregister() error {
	req, err := http.NewRequest(http.MethodDelete,
		"http://"+w.cfg.Coordinator+"/v1/nodes/"+w.id, nil)
	if err != nil {
		return err
	}
	resp, err := w.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return nil
}

func (w *worker) post(path string, body any) error {
	b, err := json.Marshal(body)
	if err != nil {
		return err
	}
	resp, err := w.client.Post("http://"+w.cfg.Coordinator+path,
		"application/json", bytes.NewReader(b))
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return fmt.Errorf("coordinator returned %d", resp.StatusCode)
	}
	return nil
}
