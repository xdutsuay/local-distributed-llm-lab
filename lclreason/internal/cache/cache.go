package cache

import (
	"crypto/sha256"
	"fmt"
	"sync"
	"time"
)

type entry struct {
	value   string
	expires time.Time
}

type Cache struct {
	mu      sync.RWMutex
	store   map[string]entry
	ttl     time.Duration
	enabled bool
}

func New(enabled bool, ttl time.Duration) *Cache {
	c := &Cache{
		store:   make(map[string]entry),
		ttl:     ttl,
		enabled: enabled,
	}
	go c.sweep()
	return c
}

func key(model, prompt string) string {
	h := sha256.Sum256([]byte(model + "\x00" + prompt))
	return fmt.Sprintf("%x", h)
}

func (c *Cache) Get(model, prompt string) (string, bool) {
	if !c.enabled {
		return "", false
	}
	c.mu.RLock()
	e, ok := c.store[key(model, prompt)]
	c.mu.RUnlock()
	if !ok || time.Now().After(e.expires) {
		return "", false
	}
	return e.value, true
}

func (c *Cache) Set(model, prompt, response string) {
	if !c.enabled {
		return
	}
	c.mu.Lock()
	c.store[key(model, prompt)] = entry{value: response, expires: time.Now().Add(c.ttl)}
	c.mu.Unlock()
}

func (c *Cache) Len() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return len(c.store)
}

func (c *Cache) sweep() {
	t := time.NewTicker(5 * time.Minute)
	for range t.C {
		now := time.Now()
		c.mu.Lock()
		for k, e := range c.store {
			if now.After(e.expires) {
				delete(c.store, k)
			}
		}
		c.mu.Unlock()
	}
}
