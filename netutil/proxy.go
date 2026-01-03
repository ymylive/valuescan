package netutil

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"golang.org/x/net/proxy"
)

func ResolveFirstEnv(keys ...string) string {
	for _, key := range keys {
		if value := strings.TrimSpace(os.Getenv(key)); value != "" {
			return value
		}
	}
	return ""
}

func ResolveBinanceProxyURL() string {
	raw := ResolveFirstEnv(
		"BINANCE_PROXY_URL",
		"BINANCE_SOCKS5_PROXY",
		"BINANCE_HTTP_PROXY",
		"VALUESCAN_SOCKS5_PROXY",
		"VALUESCAN_PROXY",
		"SOCKS5_PROXY",
		"VALUESCAN_HTTP_PROXY",
		"HTTPS_PROXY",
		"HTTP_PROXY",
		"https_proxy",
		"http_proxy",
	)
	return NormalizeProxyURL(raw)
}

func SanitizeProxyURL(raw string) string {
	if raw == "" {
		return ""
	}
	parsed, err := url.Parse(raw)
	if err != nil {
		return raw
	}
	if parsed.User != nil {
		parsed.User = url.User(parsed.User.Username())
	}
	return parsed.String()
}

func NormalizeProxyURL(raw string) string {
	if raw == "" {
		return ""
	}
	parsed, err := url.Parse(raw)
	if err != nil {
		return raw
	}
	host := parsed.Hostname()
	if host == "" {
		return raw
	}
	if isLoopbackHost(host) && isDockerEnvironment() {
		dockerHost := strings.TrimSpace(os.Getenv("BINANCE_DOCKER_PROXY_HOST"))
		if dockerHost == "" {
			dockerHost = "host.docker.internal"
		}
		port := parsed.Port()
		if port != "" {
			parsed.Host = net.JoinHostPort(dockerHost, port)
		} else {
			parsed.Host = dockerHost
		}
		return parsed.String()
	}
	return raw
}

func NewHTTPClientWithProxy(proxyURL string, timeout time.Duration) (*http.Client, error) {
	normalized := NormalizeProxyURL(proxyURL)
	if strings.TrimSpace(normalized) == "" {
		return nil, nil
	}
	transport, err := NewProxyTransport(normalized)
	if err != nil {
		return nil, err
	}
	client := &http.Client{Transport: transport}
	if timeout > 0 {
		client.Timeout = timeout
	}
	return client, nil
}

func NewProxyTransport(proxyURL string) (*http.Transport, error) {
	trimmed := strings.TrimSpace(NormalizeProxyURL(proxyURL))
	if trimmed == "" {
		return nil, nil
	}
	parsed, err := url.Parse(trimmed)
	if err != nil {
		return nil, err
	}
	if parsed.Scheme == "" {
		return nil, fmt.Errorf("proxy URL missing scheme: %s", proxyURL)
	}

	defaultTransport, ok := http.DefaultTransport.(*http.Transport)
	if !ok {
		return nil, fmt.Errorf("default transport is not *http.Transport")
	}
	transport := defaultTransport.Clone()

	switch strings.ToLower(parsed.Scheme) {
	case "http", "https":
		transport.Proxy = http.ProxyURL(parsed)
	case "socks5", "socks5h":
		dialer, err := proxy.FromURL(parsed, proxy.Direct)
		if err != nil {
			return nil, err
		}
		transport.Proxy = nil
		if contextDialer, ok := dialer.(proxy.ContextDialer); ok {
			transport.DialContext = contextDialer.DialContext
		} else {
			transport.DialContext = func(ctx context.Context, network, addr string) (net.Conn, error) {
				return dialer.Dial(network, addr)
			}
		}
	default:
		return nil, fmt.Errorf("unsupported proxy scheme: %s", parsed.Scheme)
	}

	return transport, nil
}

func isLoopbackHost(host string) bool {
	switch strings.ToLower(host) {
	case "127.0.0.1", "localhost", "::1":
		return true
	default:
		return false
	}
}

func isDockerEnvironment() bool {
	if os.Getenv("NOFX_DOCKER") == "1" {
		return true
	}
	if _, err := os.Stat("/.dockerenv"); err == nil {
		return true
	}
	if data, err := os.ReadFile("/proc/1/cgroup"); err == nil {
		if strings.Contains(string(data), "docker") || strings.Contains(string(data), "containerd") {
			return true
		}
	}
	return false
}
