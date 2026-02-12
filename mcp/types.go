package mcp

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"time"
)

const (
	ProviderDeepSeek = "deepseek"
	ProviderOpenAI   = "openai"

	DefaultDeepSeekBaseURL = "https://api.deepseek.com/v1"
	DefaultDeepSeekModel   = "deepseek-chat"
)

// Logger defines the minimum logging contract used by MCP client.
type Logger interface {
	Debugf(format string, args ...interface{})
	Infof(format string, args ...interface{})
	Warnf(format string, args ...interface{})
	Errorf(format string, args ...interface{})
}

type stdLogger struct{}

func (l *stdLogger) Debugf(format string, args ...interface{}) {
	log.Printf("[DEBUG] "+format, args...)
}

func (l *stdLogger) Infof(format string, args ...interface{}) {
	log.Printf("[INFO] "+format, args...)
}

func (l *stdLogger) Warnf(format string, args ...interface{}) {
	log.Printf("[WARN] "+format, args...)
}

func (l *stdLogger) Errorf(format string, args ...interface{}) {
	log.Printf("[ERROR] "+format, args...)
}

// Config holds full client runtime configuration.
type Config struct {
	Provider        string
	APIKey          string
	BaseURL         string
	Model           string
	MaxTokens       int
	UseFullURL      bool
	HTTPClient      *http.Client
	Logger          Logger
	MaxRetries      int
	RetryWaitBase   time.Duration
	RetryableErrors []string
	Temperature     float64
}

// ClientOption mutates config during client construction.
type ClientOption func(*Config)

// DefaultConfig returns sensible defaults for MCP client.
func DefaultConfig() *Config {
	apiKey := os.Getenv("AI_API_KEY")
	if apiKey == "" {
		apiKey = os.Getenv("DEEPSEEK_API_KEY")
	}

	return &Config{
		Provider:        ProviderDeepSeek,
		APIKey:          apiKey,
		BaseURL:         DefaultDeepSeekBaseURL,
		Model:           DefaultDeepSeekModel,
		MaxTokens:       8192,
		UseFullURL:      false,
		HTTPClient:      &http.Client{Timeout: DefaultTimeout},
		Logger:          &stdLogger{},
		MaxRetries:      MaxRetryTimes,
		RetryWaitBase:   2 * time.Second,
		RetryableErrors: append([]string(nil), retryableErrors...),
		Temperature:     MCPClientTemperature,
	}
}

// WithLogger sets custom logger.
func WithLogger(logger Logger) ClientOption {
	return func(cfg *Config) {
		if logger != nil {
			cfg.Logger = logger
		}
	}
}

// WithTimeout sets HTTP timeout.
func WithTimeout(timeout time.Duration) ClientOption {
	return func(cfg *Config) {
		if timeout > 0 {
			cfg.HTTPClient = &http.Client{Timeout: timeout}
		}
	}
}

// WithDeepSeekConfig sets DeepSeek provider configuration.
func WithDeepSeekConfig(apiKey string) ClientOption {
	return func(cfg *Config) {
		cfg.Provider = ProviderDeepSeek
		cfg.APIKey = apiKey
		cfg.BaseURL = DefaultDeepSeekBaseURL
		cfg.Model = DefaultDeepSeekModel
		cfg.UseFullURL = false
	}
}

// WithOpenAIConfig sets OpenAI-compatible configuration.
func WithOpenAIConfig(apiKey, baseURL, model string) ClientOption {
	return func(cfg *Config) {
		cfg.Provider = ProviderOpenAI
		cfg.APIKey = apiKey
		cfg.BaseURL = baseURL
		cfg.Model = model
		cfg.UseFullURL = false
	}
}

// WithCustomConfig sets fully custom provider configuration.
func WithCustomConfig(provider, apiKey, baseURL, model string, useFullURL bool) ClientOption {
	return func(cfg *Config) {
		cfg.Provider = provider
		cfg.APIKey = apiKey
		cfg.BaseURL = baseURL
		cfg.Model = model
		cfg.UseFullURL = useFullURL
	}
}

// Message is one chat message.
type Message struct {
	Role    string
	Content string
}

// Request represents a full completion request.
type Request struct {
	Model            string
	Messages         []Message
	Temperature      *float64
	MaxTokens        *int
	TopP             *float64
	FrequencyPenalty *float64
	PresencePenalty  *float64
	Stop             []string
	Tools            []map[string]any
	ToolChoice       string
	Stream           bool
}

// RequestBuilder helps build Request safely.
type RequestBuilder struct {
	req Request
}

// NewRequestBuilder creates a new request builder.
func NewRequestBuilder() *RequestBuilder {
	return &RequestBuilder{req: Request{Messages: make([]Message, 0, 2)}}
}

// WithModel sets request model.
func (b *RequestBuilder) WithModel(model string) *RequestBuilder {
	b.req.Model = model
	return b
}

// WithSystemPrompt appends a system message.
func (b *RequestBuilder) WithSystemPrompt(prompt string) *RequestBuilder {
	if prompt != "" {
		b.req.Messages = append(b.req.Messages, Message{Role: "system", Content: prompt})
	}
	return b
}

// WithUserPrompt appends a user message.
func (b *RequestBuilder) WithUserPrompt(prompt string) *RequestBuilder {
	if prompt != "" {
		b.req.Messages = append(b.req.Messages, Message{Role: "user", Content: prompt})
	}
	return b
}

// WithTemperature sets temperature.
func (b *RequestBuilder) WithTemperature(value float64) *RequestBuilder {
	b.req.Temperature = &value
	return b
}

// WithMaxTokens sets max tokens.
func (b *RequestBuilder) WithMaxTokens(value int) *RequestBuilder {
	b.req.MaxTokens = &value
	return b
}

// Build finalizes request.
func (b *RequestBuilder) Build() (*Request, error) {
	if len(b.req.Messages) == 0 {
		return nil, fmt.Errorf("request must contain at least one message")
	}
	result := b.req
	return &result, nil
}
