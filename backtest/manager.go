package backtest

import (
	"context"
	"database/sql"
)

// BacktestConfig holds backtest configuration
type BacktestConfig struct {
	RunID        string `json:"run_id"`
	CustomPrompt string `json:"custom_prompt"`
	UserID       string `json:"user_id"`
}

// Manager manages backtest operations
type Manager struct {
	db *sql.DB
}

// NewManager creates a new backtest manager
func NewManager(client interface{}) *Manager {
	return &Manager{}
}

// UseDatabase sets the database for backtest
func UseDatabase(db *sql.DB) {
	// Store database reference
}

// RestoreRuns restores backtest runs from database
func (m *Manager) RestoreRuns() error {
	return nil
}

// Start starts a backtest
func (m *Manager) Start(ctx context.Context, config BacktestConfig) (*Runner, error) {
	return &Runner{}, nil
}

// Pause pauses a backtest
func (m *Manager) Pause(runID string) error {
	return nil
}

// Resume resumes a backtest
func (m *Manager) Resume(runID string) error {
	return nil
}

// Stop stops a backtest
func (m *Manager) Stop(runID string) error {
	return nil
}
