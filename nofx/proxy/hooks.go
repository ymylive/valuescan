package proxy

import (
	"errors"
	"net/http"

	"nofx/hook"
	"nofx/logger"

	"github.com/adshao/go-binance/v2/futures"
)

// InitBinanceProxyHooks registers hooks so Binance HTTP clients use the proxy.
func InitBinanceProxyHooks() {
	if getBinanceProxyURL() == nil {
		return
	}

	hook.RegisterHook(hook.NEW_BINANCE_TRADER, func(args ...any) any {
		client, ok := args[1].(*futures.Client)
		if !ok || client == nil {
			return &hook.NewBinanceTraderResult{Err: errors.New("invalid binance client")}
		}
		client.HTTPClient = ApplyBinanceProxy(client.HTTPClient)
		return &hook.NewBinanceTraderResult{Client: client}
	})

	hook.RegisterHook(hook.SET_HTTP_CLIENT, func(args ...any) any {
		client, ok := args[0].(*http.Client)
		if !ok || client == nil {
			return &hook.SetHttpClientResult{Err: errors.New("invalid http client")}
		}
		client = ApplyBinanceProxy(client)
		return &hook.SetHttpClientResult{Client: client}
	})

	logger.Info("Binance proxy enabled for NOFX")
}
