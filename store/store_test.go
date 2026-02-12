package store

import (
	"database/sql"
	"errors"
	"path/filepath"
	"testing"
)

func newTestStore(t *testing.T) *Store {
	t.Helper()

	dbPath := filepath.Join(t.TempDir(), "store.db")
	s, err := New(dbPath)
	if err != nil {
		t.Fatalf("failed to create store: %v", err)
	}

	t.Cleanup(func() {
		_ = s.Close()
	})

	return s
}

func TestTransactionCommitsChanges(t *testing.T) {
	s := newTestStore(t)

	err := s.Transaction(func(tx *sql.Tx) error {
		_, execErr := tx.Exec(`INSERT INTO system_config (key, value) VALUES (?, ?)`, "k1", "v1")
		return execErr
	})
	if err != nil {
		t.Fatalf("unexpected transaction error: %v", err)
	}

	value, err := s.GetSystemConfig("k1")
	if err != nil {
		t.Fatalf("failed to read committed value: %v", err)
	}

	if value != "v1" {
		t.Fatalf("expected committed value %q, got %q", "v1", value)
	}
}

func TestTransactionRollsBackOnCallbackError(t *testing.T) {
	s := newTestStore(t)
	expectedErr := errors.New("force rollback")

	err := s.Transaction(func(tx *sql.Tx) error {
		_, execErr := tx.Exec(`INSERT INTO system_config (key, value) VALUES (?, ?)`, "k2", "v2")
		if execErr != nil {
			return execErr
		}
		return expectedErr
	})

	if !errors.Is(err, expectedErr) {
		t.Fatalf("expected rollback error %v, got %v", expectedErr, err)
	}

	value, err := s.GetSystemConfig("k2")
	if err != nil {
		t.Fatalf("failed to read rolled back value: %v", err)
	}

	if value != "" {
		t.Fatalf("expected no committed value after rollback, got %q", value)
	}
}
