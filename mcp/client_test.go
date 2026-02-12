package mcp

import (
	"errors"
	"net/http"
	"strings"
	"testing"
)

type noopLogger struct{}

func (l *noopLogger) Debugf(format string, args ...interface{}) {}
func (l *noopLogger) Infof(format string, args ...interface{})  {}
func (l *noopLogger) Warnf(format string, args ...interface{})  {}
func (l *noopLogger) Errorf(format string, args ...interface{}) {}

type testHooks struct {
	callFn      func(systemPrompt, userPrompt string) (string, error)
	retryableFn func(error) bool
	callCount   int
}

func (h *testHooks) call(systemPrompt, userPrompt string) (string, error) {
	h.callCount++
	if h.callFn == nil {
		return "", nil
	}
	return h.callFn(systemPrompt, userPrompt)
}

func (h *testHooks) buildMCPRequestBody(systemPrompt, userPrompt string) map[string]any {
	return map[string]any{}
}

func (h *testHooks) buildUrl() string {
	return ""
}

func (h *testHooks) buildRequest(url string, jsonData []byte) (*http.Request, error) {
	return nil, nil
}

func (h *testHooks) setAuthHeader(reqHeaders http.Header) {}

func (h *testHooks) marshalRequestBody(requestBody map[string]any) ([]byte, error) {
	return []byte("{}"), nil
}

func (h *testHooks) parseMCPResponse(body []byte) (string, error) {
	return "", nil
}

func (h *testHooks) isRetryableError(err error) bool {
	if h.retryableFn == nil {
		return false
	}
	return h.retryableFn(err)
}

func newRetryTestClient(maxRetries int) *Client {
	cfg := DefaultConfig()
	cfg.MaxRetries = maxRetries
	cfg.RetryWaitBase = 0
	cfg.Logger = &noopLogger{}

	return &Client{
		APIKey:     "test-key",
		httpClient: cfg.HTTPClient,
		logger:     cfg.Logger,
		config:     cfg,
	}
}

func TestIsRetryableErrorClassification(t *testing.T) {
	client := newRetryTestClient(1)
	client.config.RetryableErrors = []string{"timeout", "temporary failure"}

	if !client.isRetryableError(errors.New("request timeout while dialing")) {
		t.Fatal("expected timeout error to be retryable")
	}

	if client.isRetryableError(errors.New("invalid credentials")) {
		t.Fatal("expected auth error to be non-retryable")
	}
}

func TestCallWithMessagesStopsImmediatelyOnNonRetryableError(t *testing.T) {
	client := newRetryTestClient(3)
	terminalErr := errors.New("invalid request payload")
	hooks := &testHooks{
		callFn: func(systemPrompt, userPrompt string) (string, error) {
			return "", terminalErr
		},
		retryableFn: func(err error) bool {
			return false
		},
	}
	client.hooks = hooks

	_, err := client.CallWithMessages("sys", "user")
	if !errors.Is(err, terminalErr) {
		t.Fatalf("expected terminal error %v, got %v", terminalErr, err)
	}

	if hooks.callCount != 1 {
		t.Fatalf("expected one attempt for non-retryable error, got %d", hooks.callCount)
	}
}

func TestCallWithMessagesTerminatesAfterMaxRetries(t *testing.T) {
	client := newRetryTestClient(3)
	retryErr := errors.New("temporary failure")
	hooks := &testHooks{
		callFn: func(systemPrompt, userPrompt string) (string, error) {
			return "", retryErr
		},
		retryableFn: func(err error) bool {
			return true
		},
	}
	client.hooks = hooks

	_, err := client.CallWithMessages("sys", "user")
	if err == nil {
		t.Fatal("expected retry exhaustion error")
	}

	if !strings.Contains(err.Error(), "still failed after 3 retries") {
		t.Fatalf("expected retry exhaustion message, got %v", err)
	}

	if hooks.callCount != 3 {
		t.Fatalf("expected three attempts, got %d", hooks.callCount)
	}
}
