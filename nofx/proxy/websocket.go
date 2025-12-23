package proxy

import (
	"net/http"

	"github.com/gorilla/websocket"
)

// ApplyBinanceProxyToDialer updates the WebSocket dialer to use the Binance proxy.
func ApplyBinanceProxyToDialer(dialer *websocket.Dialer) *websocket.Dialer {
	proxyURL := getBinanceProxyURL()
	if proxyURL == nil {
		return dialer
	}
	if dialer == nil {
		dialer = websocket.DefaultDialer
	}
	clone := *dialer
	clone.Proxy = http.ProxyURL(proxyURL)
	return &clone
}
