package market

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestParseKlineReturnsErrorForShortRow(t *testing.T) {
	_, err := parseKline(KlineResponse{1700000000000.0, "1.0"})
	if err == nil {
		t.Fatal("expected error for short kline row")
	}
}

func TestGetKlinesReturnsErrorWhenResponseIsInvalidJSON(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte("{invalid-json"))
	}))
	defer server.Close()

	oldBaseURL := baseURL
	baseURL = server.URL
	t.Cleanup(func() {
		baseURL = oldBaseURL
	})

	client := &APIClient{client: server.Client()}
	_, err := client.GetKlines("BTCUSDT", "1m", 2)
	if err == nil {
		t.Fatal("expected JSON unmarshal error")
	}
}

func TestGetKlinesSkipsInvalidRowsAndParsesValidRows(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`[
			[1700000000000, "1.0"],
			[1700000000000, "1.0", "2.0", "0.5", "1.5", "100", 1700000060000, "150", 10, "50", "75"]
		]`))
	}))
	defer server.Close()

	oldBaseURL := baseURL
	baseURL = server.URL
	t.Cleanup(func() {
		baseURL = oldBaseURL
	})

	client := &APIClient{client: server.Client()}
	klines, err := client.GetKlines("BTCUSDT", "1m", 2)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(klines) != 1 {
		t.Fatalf("expected one parsed kline, got %d", len(klines))
	}

	if klines[0].OpenTime != 1700000000000 {
		t.Fatalf("unexpected open time: %d", klines[0].OpenTime)
	}

	if klines[0].Close != 1.5 {
		t.Fatalf("unexpected close price: %f", klines[0].Close)
	}
}
