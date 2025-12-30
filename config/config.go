package config

import (
	"os"
	"strconv"
)

// Config holds application configuration
type Config struct {
	JWTSecret     string
	APIServerPort int
}

var globalConfig *Config

// Init initializes configuration from environment variables
func Init() {
	port := 8080
	if portStr := os.Getenv("API_PORT"); portStr != "" {
		if p, err := strconv.Atoi(portStr); err == nil {
			port = p
		}
	}

	globalConfig = &Config{
		JWTSecret:     os.Getenv("JWT_SECRET"),
		APIServerPort: port,
	}

	// Generate default JWT secret if not set
	if globalConfig.JWTSecret == "" {
		globalConfig.JWTSecret = "default-jwt-secret-change-in-production"
	}
}

// Get returns the global configuration
func Get() *Config {
	if globalConfig == nil {
		Init()
	}
	return globalConfig
}
