package store

import (
	"context"
	"database/sql"
	"time"

	_ "modernc.org/sqlite"
)

type Event struct {
	ID        int64
	Kind      string
	NodeID    string
	Model     string
	Prompt    string
	Response  string
	DurationMs int64
	CreatedAt time.Time
}

type Store struct {
	db *sql.DB
}

func Open(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	s := &Store{db: db}
	return s, s.migrate()
}

func (s *Store) Close() error { return s.db.Close() }

func (s *Store) migrate() error {
	_, err := s.db.Exec(`
		CREATE TABLE IF NOT EXISTS events (
			id          INTEGER PRIMARY KEY AUTOINCREMENT,
			kind        TEXT NOT NULL,
			node_id     TEXT,
			model       TEXT,
			prompt      TEXT,
			response    TEXT,
			duration_ms INTEGER,
			created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
		);
		CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
		CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
	`)
	return err
}

func (s *Store) Log(ctx context.Context, e Event) error {
	_, err := s.db.ExecContext(ctx,
		`INSERT INTO events (kind, node_id, model, prompt, response, duration_ms)
		 VALUES (?, ?, ?, ?, ?, ?)`,
		e.Kind, e.NodeID, e.Model, e.Prompt, e.Response, e.DurationMs,
	)
	return err
}

func (s *Store) Recent(ctx context.Context, limit int) ([]Event, error) {
	rows, err := s.db.QueryContext(ctx,
		`SELECT id, kind, node_id, model, prompt, response, duration_ms, created_at
		 FROM events ORDER BY id DESC LIMIT ?`, limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var events []Event
	for rows.Next() {
		var e Event
		if err := rows.Scan(&e.ID, &e.Kind, &e.NodeID, &e.Model,
			&e.Prompt, &e.Response, &e.DurationMs, &e.CreatedAt); err != nil {
			return nil, err
		}
		events = append(events, e)
	}
	return events, rows.Err()
}
