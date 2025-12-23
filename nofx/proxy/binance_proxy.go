package proxy

import (
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"

	"nofx/logger"
)

const binanceProxyEnv = "NOFX_BINANCE_PROXY"

var (
	binanceProxyOnce sync.Once
	binanceProxyURL  *url.URL
)

func getBinanceProxyURL() *url.URL {
	binanceProxyOnce.Do(func() {
		raw := strings.TrimSpace(os.Getenv(binanceProxyEnv))
		if raw == "" {
			return
		}
		proxyURL, err := url.Parse(raw)
		if err != nil || proxyURL.Scheme == "" || proxyURL.Host == "" {
			logger.Warnf("Invalid %s value, proxy disabled", binanceProxyEnv)
			return
		}
		if proxyURL.Scheme != "http" && proxyURL.Scheme != "https" {
			logger.Warnf("%s must be http or https, proxy disabled", binanceProxyEnv)
			return
		}
		binanceProxyURL = proxyURL
	})
	return binanceProxyURL
}

// ApplyBinanceProxy updates the HTTP client to use the configured Binance proxy.
func ApplyBinanceProxy(client *http.Client) *http.Client {
	proxyURL := getBinanceProxyURL()
	if proxyURL == nil {
		return client
	}
	if client == nil {
		client = &http.Client{Timeout: 30 * time.Second}
	}

	transport := http.DefaultTransport.(*http.Transport).Clone()
	if client.Transport != nil {
		if base, ok := client.Transport.(*http.Transport); ok {
			transport = base.Clone()
		}
	}
	transport.Proxy = http.ProxyURL(proxyURL)
	client.Transport = transport
	return client
}

// NewBinanceHTTPClient creates an HTTP client with Binance proxy support.
func NewBinanceHTTPClient(timeout time.Duration) *http.Client {
	client := &http.Client{Timeout: timeout}
	return ApplyBinanceProxy(client)
}
