package chain

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"text/template"
	"time"
)

// Invoker is anything that can run an inference request.
type Invoker interface {
	Invoke(ctx context.Context, model, prompt string) (string, error)
}

type Engine struct {
	loader      *Loader
	invoker     Invoker
	defaultName string
}

func NewEngine(loader *Loader, invoker Invoker, defaultName string) *Engine {
	return &Engine{loader: loader, invoker: invoker, defaultName: defaultName}
}

type Result struct {
	Chain    string        `json:"chain"`
	Steps    []StepResult  `json:"steps"`
	Output   string        `json:"output"`
	Duration time.Duration `json:"duration_ms"`
}

type StepResult struct {
	Name     string        `json:"name"`
	Output   string        `json:"output"`
	Duration time.Duration `json:"duration_ms"`
	Error    string        `json:"error,omitempty"`
}

func (e *Engine) Run(ctx context.Context, chainName, input, model string) (*Result, error) {
	if chainName == "" {
		chainName = e.defaultName
	}
	def, ok := e.loader.Get(chainName)
	if !ok {
		// No chain defined — direct passthrough.
		out, err := e.invoker.Invoke(ctx, model, input)
		if err != nil {
			return nil, err
		}
		return &Result{Chain: "direct", Output: out}, nil
	}

	res := &Result{Chain: chainName}
	start := time.Now()
	priorOutput := input

	for _, step := range def.Steps {
		stepStart := time.Now()
		sr := StepResult{Name: step.Name}

		prompt, err := renderTemplate(step.PromptTemplate, map[string]string{
			"Input":       input,
			"PriorOutput": priorOutput,
		})
		if err != nil {
			return nil, fmt.Errorf("step %q template: %w", step.Name, err)
		}

		m := model
		if step.Model != "" {
			m = step.Model
		}

		out, err := e.invoker.Invoke(ctx, m, prompt)
		sr.Duration = time.Since(stepStart)
		if err != nil {
			sr.Error = err.Error()
			res.Steps = append(res.Steps, sr)
			return res, fmt.Errorf("step %q: %w", step.Name, err)
		}

		if step.ExtractKey != "" {
			if extracted, ok := extractJSON(out, step.ExtractKey); ok {
				out = extracted
			}
		}

		sr.Output = out
		priorOutput = out
		res.Steps = append(res.Steps, sr)
	}

	res.Output = priorOutput
	res.Duration = time.Since(start)
	return res, nil
}

func renderTemplate(tmpl string, data map[string]string) (string, error) {
	t, err := template.New("").Parse(tmpl)
	if err != nil {
		return "", err
	}
	var buf bytes.Buffer
	if err := t.Execute(&buf, data); err != nil {
		return "", err
	}
	return buf.String(), nil
}

func extractJSON(raw, key string) (string, bool) {
	raw = strings.TrimSpace(raw)
	// strip markdown fences
	if strings.HasPrefix(raw, "```") {
		raw = strings.TrimPrefix(raw, "```json")
		raw = strings.TrimPrefix(raw, "```")
		if idx := strings.LastIndex(raw, "```"); idx >= 0 {
			raw = raw[:idx]
		}
	}
	var m map[string]any
	if err := json.Unmarshal([]byte(raw), &m); err != nil {
		return "", false
	}
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s, true
		}
		b, _ := json.Marshal(v)
		return string(b), true
	}
	return "", false
}
