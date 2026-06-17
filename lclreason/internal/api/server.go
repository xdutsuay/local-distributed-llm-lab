package api

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/xdutsuay/lclreason/internal/cache"
	"github.com/xdutsuay/lclreason/internal/chain"
	"github.com/xdutsuay/lclreason/internal/dispatch"
	"github.com/xdutsuay/lclreason/internal/registry"
	"github.com/xdutsuay/lclreason/internal/store"
)

type Server struct {
	http     *http.Server
	handlers *Handlers
}

func New(port int,
	reg *registry.Registry,
	dis *dispatch.Dispatcher,
	eng *chain.Engine,
	cch *cache.Cache,
	st *store.Store,
) *Server {
	h := &Handlers{
		reg:   reg,
		dis:   dis,
		eng:   eng,
		cache: cch,
		store: st,
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", h.Health)
	mux.HandleFunc("GET /v1/nodes", h.ListNodes)
	mux.HandleFunc("POST /v1/nodes/register", h.RegisterNode)
	mux.HandleFunc("POST /v1/nodes/heartbeat", h.Heartbeat)
	mux.HandleFunc("DELETE /v1/nodes/{id}", h.DeregisterNode)
	mux.HandleFunc("POST /v1/chat/completions", h.ChatCompletions)
	mux.HandleFunc("GET /v1/models", h.ListModels)
	mux.HandleFunc("GET /v1/events", h.ListEvents)
	mux.HandleFunc("GET /", h.Dashboard)

	return &Server{
		http: &http.Server{
			Addr:         fmt.Sprintf(":%d", port),
			Handler:      logging(mux),
			ReadTimeout:  30 * time.Second,
			WriteTimeout: 180 * time.Second,
			IdleTimeout:  60 * time.Second,
		},
		handlers: h,
	}
}

func (s *Server) Start() error {
	log.Printf("lclreason listening on %s", s.http.Addr)
	return s.http.ListenAndServe()
}

func (s *Server) Shutdown(ctx context.Context) error {
	return s.http.Shutdown(ctx)
}

func logging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s %s", r.Method, r.URL.Path, time.Since(start))
	})
}
