package main

import (
	"context"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/xdutsuay/lclreason/internal/api"
	"github.com/xdutsuay/lclreason/internal/cache"
	"github.com/xdutsuay/lclreason/internal/chain"
	"github.com/xdutsuay/lclreason/internal/config"
	"github.com/xdutsuay/lclreason/internal/dispatch"
	"github.com/xdutsuay/lclreason/internal/registry"
	"github.com/xdutsuay/lclreason/internal/store"
)

func main() {
	cfgPath := flag.String("config", "config.yaml", "path to config file")
	mode := flag.String("mode", "", "coordinator or worker (overrides config)")
	port := flag.Int("port", 0, "port override")
	flag.Parse()

	cfg, err := config.Load(*cfgPath)
	if err != nil {
		log.Fatalf("config: %v", err)
	}
	if *mode != "" {
		cfg.Mode = *mode
	}
	if *port != 0 {
		cfg.Port = *port
	}

	switch cfg.Mode {
	case "coordinator":
		runCoordinator(cfg)
	case "worker":
		runWorker(cfg)
	default:
		log.Fatalf("unknown mode %q — use coordinator or worker", cfg.Mode)
	}
}

func runCoordinator(cfg *config.Config) {
	st, err := store.Open(cfg.DB)
	if err != nil {
		log.Fatalf("store: %v", err)
	}
	defer st.Close()

	reg := registry.New(cfg.OfflineAfter.Duration)
	cch := cache.New(cfg.Cache.Enabled, cfg.Cache.TTL.Duration)
	dis := dispatch.New(reg)

	loader, err := chain.NewLoader(cfg.Chain.Dir)
	if err != nil {
		log.Fatalf("chain loader: %v", err)
	}
	eng := chain.NewEngine(loader, dis, cfg.Chain.Default)

	srv := api.New(cfg.Port, reg, dis, eng, cch, st)

	// Sweep stale nodes every heartbeat interval.
	go func() {
		t := time.NewTicker(cfg.Heartbeat.Duration)
		for range t.C {
			reg.Sweep()
		}
	}()

	go func() {
		if err := srv.Start(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server: %v", err)
		}
	}()

	waitForShutdown(func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = srv.Shutdown(ctx)
	})
}

func runWorker(cfg *config.Config) {
	if cfg.Coordinator == "" {
		log.Fatal("worker mode requires coordinator address in config (coordinator: host:port)")
	}
	w := &worker{cfg: cfg, client: &http.Client{Timeout: 10 * time.Second}}
	if err := w.register(); err != nil {
		log.Fatalf("register with coordinator: %v", err)
	}
	log.Printf("worker registered with %s", cfg.Coordinator)

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)

	t := time.NewTicker(cfg.Heartbeat.Duration)
	defer t.Stop()
	for {
		select {
		case <-t.C:
			if err := w.heartbeat(); err != nil {
				log.Printf("heartbeat error: %v", err)
			}
		case <-stop:
			_ = w.deregister()
			log.Println("worker deregistered, exiting")
			return
		}
	}
}

func waitForShutdown(cleanup func()) {
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop
	log.Println("shutting down…")
	cleanup()
}
