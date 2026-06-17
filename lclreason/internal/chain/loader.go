package chain

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

type ChainDef struct {
	Name  string `yaml:"name"`
	Steps []Step `yaml:"steps"`
}

type Step struct {
	Name           string `yaml:"name"`
	PromptTemplate string `yaml:"prompt_template"`
	Model          string `yaml:"model"`
	ExtractKey     string `yaml:"extract_key"` // pull this key from JSON response
	UseOutputOf    string `yaml:"use_output_of"` // inject prior step's output as {{.PriorOutput}}
}

type Loader struct {
	dir    string
	chains map[string]ChainDef
}

func NewLoader(dir string) (*Loader, error) {
	l := &Loader{dir: dir, chains: make(map[string]ChainDef)}
	return l, l.loadAll()
}

func (l *Loader) loadAll() error {
	entries, err := os.ReadDir(l.dir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil // chains dir optional
		}
		return err
	}
	for _, e := range entries {
		if e.IsDir() || filepath.Ext(e.Name()) != ".yaml" {
			continue
		}
		name := e.Name()[:len(e.Name())-5]
		if err := l.load(name); err != nil {
			return fmt.Errorf("chain %q: %w", name, err)
		}
	}
	return nil
}

func (l *Loader) load(name string) error {
	f, err := os.Open(filepath.Join(l.dir, name+".yaml"))
	if err != nil {
		return err
	}
	defer f.Close()
	var def ChainDef
	if err := yaml.NewDecoder(f).Decode(&def); err != nil {
		return err
	}
	if def.Name == "" {
		def.Name = name
	}
	l.chains[name] = def
	return nil
}

func (l *Loader) Get(name string) (ChainDef, bool) {
	c, ok := l.chains[name]
	return c, ok
}

func (l *Loader) Names() []string {
	names := make([]string, 0, len(l.chains))
	for k := range l.chains {
		names = append(names, k)
	}
	return names
}
