package backtest

// Runner represents a backtest runner
type Runner struct {
	runID string
}

// Metadata holds backtest metadata
type Metadata struct {
	RunID  string `json:"run_id"`
	Status string `json:"status"`
}

// CurrentMetadata returns current metadata
func (r *Runner) CurrentMetadata() Metadata {
	return Metadata{
		RunID:  r.runID,
		Status: "running",
	}
}
