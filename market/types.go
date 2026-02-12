package market

// Alert represents a runtime alert emitted by market monitoring logic.
type Alert struct {
	Symbol    string
	Message   string
	Timestamp int64
}

// ExchangeInfo mirrors Binance exchange metadata response.
type ExchangeInfo struct {
	Symbols []ExchangeSymbol `json:"symbols"`
}

// ExchangeSymbol mirrors one symbol entry from exchange info.
type ExchangeSymbol struct {
	Symbol       string `json:"symbol"`
	Status       string `json:"status"`
	ContractType string `json:"contractType"`
}

// KlineResponse is one raw kline row from Binance API.
type KlineResponse []interface{}

// Kline is normalized kline data used across market package.
type Kline struct {
	OpenTime            int64
	Open                float64
	High                float64
	Low                 float64
	Close               float64
	Volume              float64
	CloseTime           int64
	QuoteVolume         float64
	Trades              int
	TakerBuyBaseVolume  float64
	TakerBuyQuoteVolume float64
}

// PriceTicker mirrors Binance ticker/price response.
type PriceTicker struct {
	Symbol string `json:"symbol"`
	Price  string `json:"price"`
}

// OIData contains open-interest snapshot values.
type OIData struct {
	Latest  float64
	Average float64
}

// KlineBar is compact OHLCV row for formatted timeframe output.
type KlineBar struct {
	Time   int64
	Open   float64
	High   float64
	Low    float64
	Close  float64
	Volume float64
}

// IntradayData stores short timeframe feature series.
type IntradayData struct {
	MidPrices   []float64
	EMA20Values []float64
	MACDValues  []float64
	RSI7Values  []float64
	RSI14Values []float64
	Volume      []float64
	ATR14       float64
}

// LongerTermData stores longer timeframe feature series.
type LongerTermData struct {
	EMA20         float64
	EMA50         float64
	ATR3          float64
	ATR14         float64
	CurrentVolume float64
	AverageVolume float64
	MACDValues    []float64
	RSI14Values   []float64
}

// TimeframeSeriesData stores multi-timeframe sequence features.
type TimeframeSeriesData struct {
	Timeframe   string
	Klines      []KlineBar
	MidPrices   []float64
	EMA20Values []float64
	EMA50Values []float64
	MACDValues  []float64
	RSI7Values  []float64
	RSI14Values []float64
	Volume      []float64
	BOLLUpper   []float64
	BOLLMiddle  []float64
	BOLLLower   []float64
	ATR14       float64
}

// Data is the aggregated market snapshot consumed by strategy modules.
type Data struct {
	Symbol            string
	CurrentPrice      float64
	PriceChange1h     float64
	PriceChange4h     float64
	CurrentEMA20      float64
	CurrentMACD       float64
	CurrentRSI7       float64
	OpenInterest      *OIData
	FundingRate       float64
	IntradaySeries    *IntradayData
	LongerTermContext *LongerTermData
	TimeframeData     map[string]*TimeframeSeriesData
}
