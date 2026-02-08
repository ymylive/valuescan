package store

import (
    "database/sql"
    "fmt"
    "nofx/logger"
    "sync"

    _ "modernc.org/sqlite"
)

// Store provides database access for lightweight config storage.
type Store struct {
    db         *sql.DB
    userConfig *UserConfigStore
    mu         sync.RWMutex
}

// New creates a Store with the SQLite database at dbPath.
func New(dbPath string) (*Store, error) {
    db, err := sql.Open("sqlite", dbPath)
    if err != nil {
        return nil, fmt.Errorf("failed to open database: %w", err)
    }

    db.SetMaxOpenConns(5)
    db.SetMaxIdleConns(2)

    if _, err := db.Exec(`PRAGMA foreign_keys = ON`); err != nil {
        db.Close()
        return nil, fmt.Errorf("failed to enable foreign keys: %w", err)
    }

    if _, err := db.Exec("PRAGMA journal_mode=WAL"); err != nil {
        db.Close()
        return nil, fmt.Errorf("failed to set journal_mode: %w", err)
    }

    if _, err := db.Exec("PRAGMA synchronous=NORMAL"); err != nil {
        db.Close()
        return nil, fmt.Errorf("failed to set synchronous: %w", err)
    }

    if _, err := db.Exec("PRAGMA busy_timeout = 5000"); err != nil {
        db.Close()
        return nil, fmt.Errorf("failed to set busy_timeout: %w", err)
    }

    s := &Store{db: db}
    if err := s.initTables(); err != nil {
        db.Close()
        return nil, fmt.Errorf("failed to initialize table structure: %w", err)
    }

    logger.Info("Database enabled WAL mode and NORMAL sync")
    return s, nil
}

// NewFromDB creates Store from existing database connection.
func NewFromDB(db *sql.DB) *Store {
    return &Store{db: db}
}

func (s *Store) initTables() error {
    if _, err := s.db.Exec(`
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    `); err != nil {
        return fmt.Errorf("failed to create system_config table: %w", err)
    }

    if err := s.UserConfig().InitSchema(); err != nil {
        return fmt.Errorf("failed to initialize user config tables: %w", err)
    }

    return nil
}

// UserConfig gets user config storage.
func (s *Store) UserConfig() *UserConfigStore {
    s.mu.Lock()
    defer s.mu.Unlock()
    if s.userConfig == nil {
        s.userConfig = &UserConfigStore{db: s.db}
    }
    return s.userConfig
}

// Close closes database connection.
func (s *Store) Close() error {
    return s.db.Close()
}

// DB returns the underlying database connection.
func (s *Store) DB() *sql.DB {
    return s.db
}

// GetSystemConfig gets a system configuration value by key.
func (s *Store) GetSystemConfig(key string) (string, error) {
    var value string
    err := s.db.QueryRow(`SELECT value FROM system_config WHERE key = ?`, key).Scan(&value)
    if err == sql.ErrNoRows {
        return "", nil
    }
    return value, err
}

// SetSystemConfig sets a system configuration value.
func (s *Store) SetSystemConfig(key, value string) error {
    _, err := s.db.Exec(`
        INSERT INTO system_config (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    `, key, value)
    return err
}

// Transaction executes a database transaction.
func (s *Store) Transaction(fn func(tx *sql.Tx) error) error {
    tx, err := s.db.Begin()
    if err != nil {
        return fmt.Errorf("failed to begin transaction: %w", err)
    }

    if err := fn(tx); err != nil {
        tx.Rollback()
        return err
    }

    if err := tx.Commit(); err != nil {
        return fmt.Errorf("failed to commit transaction: %w", err)
    }
    return nil
}
