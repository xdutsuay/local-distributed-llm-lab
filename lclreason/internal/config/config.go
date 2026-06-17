package config

import (
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Mode        string      `yaml:"mode"`
	Port        int         `yaml:"port"`
	Coordinator string      `yaml:"coordinator"`
	DB          string      `yaml:"db"`
	Chain       ChainConfig `yaml:"chain"`
	Cache       CacheConfig `yaml:"cache"`
	Heartbeat   YAMLDur     `yaml:"heartbeat"`
	OfflineAfter YAMLDur   `yaml:"offline_after"`
}

type ChainConfig struct {
	Dir     string `yaml:"dir"`
	Default string `yaml:"default"`
}

type CacheConfig struct {
	Enabled bool    `yaml:"enabled"`
	TTL     YAMLDur `yaml:"ttl"`
}

// YAMLDur wraps time.Duration for YAML unmarshalling.
type YAMLDur struct{ time.Duration }

func (d *YAMLDur) UnmarshalYAML(v *yaml.Node) error {
	dur, err := time.ParseDuration(v.Value)
	if err != nil {
		return err
	}
	d.Duration = dur
	return nil
}

func Load(path string) (*Config, error) {
	cfg := defaults()
	f, err := os.Open(path)
	if err != nil {
		if os.IsNotExist(err) {
			return cfg, nil
		}
		return nil, err
	}
	defer f.Close()
	return cfg, yaml.NewDecoder(f).Decode(cfg)
}

func defaults() *Config {
	return &Config{
		Mode:         "coordinator",
		Port:         8080,
		DB:           "lclreason.db",
		Chain:        ChainConfig{Dir: "chains", Default: "default"},
		Cache:        CacheConfig{Enabled: true, TTL: YAMLDur{time.Hour}},
		Heartbeat:    YAMLDur{5 * time.Second},
		OfflineAfter: YAMLDur{15 * time.Second},
	}
}
