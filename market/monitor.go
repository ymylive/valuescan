package market

import (
	"encoding/json"
	"fmt"
	"log"
	"runtime"
	"strings"
	"sync"
	"time"
)

type WSMonitor struct {
	wsClient       *WSClient
	combinedClient *CombinedStreamsClient
	symbols        []string
	featuresMap    sync.Map
	alertsChan     chan Alert
	klineDataMap3m *LRUCache // Store K-line historical data for each trading pair with LRU eviction
	klineDataMap4h *LRUCache // Store K-line historical data for each trading pair with LRU eviction
	tickerDataMap  *LRUCache // Store ticker data for each trading pair with LRU eviction
	batchSize      int
	filterSymbols  sync.Map // Use sync.Map to store monitored coins and their status
	symbolStats    sync.Map // Store symbol statistics
	FilterSymbol   []string // Filtered symbols
	cleanupTicker  *time.Ticker
	stopCleanup    chan struct{}
}
type SymbolStats struct {
	LastActiveTime   time.Time
	AlertCount       int
	VolumeSpikeCount int
	LastAlertTime    time.Time
	Score            float64 // Composite score
}

var WSMonitorCli *WSMonitor
var subKlineTime = []string{"3m", "4h"} // Manage K-line periods for subscription streams

func NewWSMonitor(batchSize int) *WSMonitor {
	WSMonitorCli = &WSMonitor{
		wsClient:       NewWSClient(),
		combinedClient: NewCombinedStreamsClient(batchSize),
		alertsChan:     make(chan Alert, 1000),
		batchSize:      batchSize,
		klineDataMap3m: NewLRUCache(500, 24*time.Hour), // Max 500 symbols, 24h TTL
		klineDataMap4h: NewLRUCache(500, 24*time.Hour), // Max 500 symbols, 24h TTL
		tickerDataMap:  NewLRUCache(500, 24*time.Hour), // Max 500 symbols, 24h TTL
		stopCleanup:    make(chan struct{}),
	}
	// Start periodic cleanup goroutine
	WSMonitorCli.startPeriodicCleanup()
	return WSMonitorCli
}

func (m *WSMonitor) Initialize(coins []string) error {
	log.Println("Initializing WebSocket monitor...")
	// Get trading pair information
	apiClient := NewAPIClient()
	// If trading pairs are not specified, use all trading pairs from the market
	if len(coins) == 0 {
		exchangeInfo, err := apiClient.GetExchangeInfo()
		if err != nil {
			return err
		}
		// Filter perpetual contract trading pairs -- only use for testing
		//exchangeInfo.Symbols = exchangeInfo.Symbols[0:2]
		for _, symbol := range exchangeInfo.Symbols {
			if symbol.Status == "TRADING" && symbol.ContractType == "PERPETUAL" && strings.HasSuffix(strings.ToUpper(symbol.Symbol), "USDT") {
				m.symbols = append(m.symbols, symbol.Symbol)
				m.filterSymbols.Store(symbol.Symbol, true)
			}
		}
	} else {
		m.symbols = coins
	}

	log.Printf("Found %d trading pairs", len(m.symbols))
	// Initialize historical data
	if err := m.initializeHistoricalData(); err != nil {
		log.Printf("Failed to initialize historical data: %v", err)
	}

	return nil
}

func (m *WSMonitor) initializeHistoricalData() error {
	apiClient := NewAPIClient()

	var wg sync.WaitGroup
	semaphore := make(chan struct{}, 10) // Limit concurrency to 10

	for _, symbol := range m.symbols {
		wg.Add(1)
		semaphore <- struct{}{}

		go func(s string) {
			defer wg.Done()
			defer func() { <-semaphore }()

			// Exponential backoff for rate limiting
			maxRetries := 3
			for retry := 0; retry < maxRetries; retry++ {
				err1 := m.fetchAndStoreKlinesWithRetry(apiClient, s, "3m", m.klineDataMap3m, retry)
				err2 := m.fetchAndStoreKlinesWithRetry(apiClient, s, "4h", m.klineDataMap4h, retry)

				if err1 == nil && err2 == nil {
					break
				}

				if retry < maxRetries-1 {
					// Exponential backoff: 1s, 2s, 4s
					backoff := time.Duration(1<<uint(retry)) * time.Second
					time.Sleep(backoff)
				}
			}
		}(symbol)
	}

	wg.Wait()
	return nil
}

func (m *WSMonitor) fetchAndStoreKlinesWithRetry(apiClient *APIClient, symbol, interval string, cache *LRUCache, retryCount int) error {
	klines, err := apiClient.GetKlines(symbol, interval, 100)
	if err != nil {
		log.Printf("Failed to get %s historical data (%s) [retry %d]: %v", symbol, interval, retryCount, err)
		return err
	}
	if len(klines) > 0 {
		cache.Set(symbol, klines)
		log.Printf("Loaded %s historical K-line data-%s: %d entries", symbol, interval, len(klines))
	}
	return nil
}

// startPeriodicCleanup runs cleanup every hour to remove expired entries and log memory stats
func (m *WSMonitor) startPeriodicCleanup() {
	m.cleanupTicker = time.NewTicker(1 * time.Hour)
	go func() {
		for {
			select {
			case <-m.cleanupTicker.C:
				removed3m := m.klineDataMap3m.CleanExpired()
				removed4h := m.klineDataMap4h.CleanExpired()
				removedTicker := m.tickerDataMap.CleanExpired()

				size3m, cap3m := m.klineDataMap3m.Stats()
				size4h, cap4h := m.klineDataMap4h.Stats()
				sizeTk, capTk := m.tickerDataMap.Stats()

				var mem runtime.MemStats
				runtime.ReadMemStats(&mem)

				log.Printf("Cleanup: removed %d 3m, %d 4h, %d tickers | cache: 3m=%d/%d 4h=%d/%d ticker=%d/%d | mem: alloc=%dMB sys=%dMB",
					removed3m, removed4h, removedTicker,
					size3m, cap3m, size4h, cap4h, sizeTk, capTk,
					mem.Alloc/1024/1024, mem.Sys/1024/1024)
			case <-m.stopCleanup:
				m.cleanupTicker.Stop()
				return
			}
		}
	}()
}

func (m *WSMonitor) Start(coins []string) {
	log.Printf("Starting WebSocket real-time monitoring...")
	// Initialize trading pairs
	err := m.Initialize(coins)
	if err != nil {
		log.Printf("❌ Failed to initialize coins: %v", err)
		return
	}

	err = m.combinedClient.Connect()
	if err != nil {
		log.Printf("❌ Failed to batch subscribe to streams: %v", err)
		return
	}
	// Subscribe to all trading pairs
	err = m.subscribeAll()
	if err != nil {
		log.Printf("❌ Failed to subscribe to coin trading pairs: %v", err)
		return
	}
}

// subscribeSymbol registers listener
func (m *WSMonitor) subscribeSymbol(symbol, st string) []string {
	var streams []string
	stream := fmt.Sprintf("%s@kline_%s", strings.ToLower(symbol), st)
	ch := m.combinedClient.AddSubscriber(stream, 100)
	streams = append(streams, stream)
	go m.handleKlineData(symbol, ch, st)

	return streams
}
func (m *WSMonitor) subscribeAll() error {
	// Execute batch subscription
	log.Println("Starting to subscribe to all trading pairs...")
	for _, symbol := range m.symbols {
		for _, st := range subKlineTime {
			m.subscribeSymbol(symbol, st)
		}
	}
	for _, st := range subKlineTime {
		err := m.combinedClient.BatchSubscribeKlines(m.symbols, st)
		if err != nil {
			log.Printf("❌ Failed to subscribe to %s K-line: %v", st, err)
			return err
		}
	}
	log.Println("All trading pair subscriptions completed")
	return nil
}

func (m *WSMonitor) handleKlineData(symbol string, ch <-chan []byte, _time string) {
	for data := range ch {
		var klineData KlineWSData
		if err := json.Unmarshal(data, &klineData); err != nil {
			log.Printf("Failed to parse Kline data: %v", err)
			continue
		}
		m.processKlineUpdate(symbol, klineData, _time)
	}
}

func (m *WSMonitor) getKlineDataMap(_time string) *LRUCache {
	if _time == "3m" {
		return m.klineDataMap3m
	} else if _time == "4h" {
		return m.klineDataMap4h
	}
	// Return empty cache for unknown intervals
	return NewLRUCache(10, 1*time.Hour)
}
func (m *WSMonitor) processKlineUpdate(symbol string, wsData KlineWSData, _time string) {
	// Convert WebSocket data to Kline structure
	kline := Kline{
		OpenTime:  wsData.Kline.StartTime,
		CloseTime: wsData.Kline.CloseTime,
		Trades:    wsData.Kline.NumberOfTrades,
	}
	kline.Open, _ = parseFloat(wsData.Kline.OpenPrice)
	kline.High, _ = parseFloat(wsData.Kline.HighPrice)
	kline.Low, _ = parseFloat(wsData.Kline.LowPrice)
	kline.Close, _ = parseFloat(wsData.Kline.ClosePrice)
	kline.Volume, _ = parseFloat(wsData.Kline.Volume)
	kline.QuoteVolume, _ = parseFloat(wsData.Kline.QuoteVolume)
	kline.TakerBuyBaseVolume, _ = parseFloat(wsData.Kline.TakerBuyBaseVolume)
	kline.TakerBuyQuoteVolume, _ = parseFloat(wsData.Kline.TakerBuyQuoteVolume)

	klineDataMap := m.getKlineDataMap(_time)

	// Fast path: update existing entry in-place with a single lock acquisition
	updated := klineDataMap.UpdateValue(symbol, func(val interface{}) interface{} {
		klines := val.([]Kline)
		if len(klines) > 0 && klines[len(klines)-1].OpenTime == kline.OpenTime {
			// In-place update of current kline — no slice reallocation
			klines[len(klines)-1] = kline
		} else {
			// Append new kline
			klines = append(klines, kline)
			// Maintain max length by shifting without new allocation when possible
			if len(klines) > 100 {
				copy(klines, klines[1:])
				klines = klines[:100]
			}
		}
		return klines
	})

	// Slow path: first kline for this symbol, use Set
	if !updated {
		klineDataMap.Set(symbol, []Kline{kline})
	}
}

func (m *WSMonitor) GetCurrentKlines(symbol string, duration string) ([]Kline, error) {
	// Check if each incoming symbol exists internally, if not subscribe to it
	value, exists := m.getKlineDataMap(duration).Get(symbol)
	if !exists {
		// If WS data is not initialized, use API separately - compatibility code (prevents trader from running when not initialized)
		apiClient := NewAPIClient()
		klines, err := apiClient.GetKlines(symbol, duration, 100)
		if err != nil {
			return nil, fmt.Errorf("Failed to get %v-minute K-line: %v", duration, err)
		}

		// Dynamically cache into cache
		m.getKlineDataMap(duration).Set(strings.ToUpper(symbol), klines)

		// Subscribe to WebSocket stream
		subStr := m.subscribeSymbol(symbol, duration)
		subErr := m.combinedClient.subscribeStreams(subStr)
		log.Printf("Dynamic subscription to stream: %v", subStr)
		if subErr != nil {
			log.Printf("Warning: Failed to dynamically subscribe to %v-minute K-line: %v (using API data)", duration, subErr)
		}

		// ✅ FIX: Return deep copy instead of reference
		result := make([]Kline, len(klines))
		copy(result, klines)
		return result, nil
	}

	// ✅ FIX: Return deep copy instead of reference, avoid concurrent race conditions
	klines := value.([]Kline)
	result := make([]Kline, len(klines))
	copy(result, klines)
	return result, nil
}

func (m *WSMonitor) Close() {
	m.wsClient.Close()
	close(m.alertsChan)
	close(m.stopCleanup)
}
