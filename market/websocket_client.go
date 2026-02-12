package market

import (
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

type WSClient struct {
	conn         *websocket.Conn
	mu           sync.RWMutex
	subscribers  map[string]chan []byte
	reconnect    bool
	done         chan struct{}
	reconnectMu  sync.Mutex
	reconnecting bool
}

type WSMessage struct {
	Stream string          `json:"stream"`
	Data   json.RawMessage `json:"data"`
}

type KlineWSData struct {
	EventType string `json:"e"`
	EventTime int64  `json:"E"`
	Symbol    string `json:"s"`
	Kline     struct {
		StartTime           int64  `json:"t"`
		CloseTime           int64  `json:"T"`
		Symbol              string `json:"s"`
		Interval            string `json:"i"`
		FirstTradeID        int64  `json:"f"`
		LastTradeID         int64  `json:"L"`
		OpenPrice           string `json:"o"`
		ClosePrice          string `json:"c"`
		HighPrice           string `json:"h"`
		LowPrice            string `json:"l"`
		Volume              string `json:"v"`
		NumberOfTrades      int    `json:"n"`
		IsFinal             bool   `json:"x"`
		QuoteVolume         string `json:"q"`
		TakerBuyBaseVolume  string `json:"V"`
		TakerBuyQuoteVolume string `json:"Q"`
	} `json:"k"`
}

type TickerWSData struct {
	EventType          string `json:"e"`
	EventTime          int64  `json:"E"`
	Symbol             string `json:"s"`
	PriceChange        string `json:"p"`
	PriceChangePercent string `json:"P"`
	WeightedAvgPrice   string `json:"w"`
	LastPrice          string `json:"c"`
	LastQty            string `json:"Q"`
	OpenPrice          string `json:"o"`
	HighPrice          string `json:"h"`
	LowPrice           string `json:"l"`
	Volume             string `json:"v"`
	QuoteVolume        string `json:"q"`
	OpenTime           int64  `json:"O"`
	CloseTime          int64  `json:"C"`
	FirstID            int64  `json:"F"`
	LastID             int64  `json:"L"`
	Count              int    `json:"n"`
}

func NewWSClient() *WSClient {
	return &WSClient{
		subscribers: make(map[string]chan []byte),
		reconnect:   true,
		done:        make(chan struct{}),
	}
}

func (w *WSClient) Connect() error {
	dialer := websocket.Dialer{
		HandshakeTimeout: 10 * time.Second,
	}

	conn, _, err := dialer.Dial("wss://ws-fapi.binance.com/ws-fapi/v1", nil)
	if err != nil {
		return fmt.Errorf("WebSocket connection failed: %v", err)
	}

	w.mu.Lock()
	oldConn := w.conn
	w.conn = conn
	w.mu.Unlock()

	if oldConn != nil {
		oldConn.Close()
	}

	log.Println("WebSocket connected successfully")

	// Start message reading loop
	go w.readMessages()

	return nil
}

func (w *WSClient) SubscribeKline(symbol, interval string) error {
	stream := fmt.Sprintf("%s@kline_%s", symbol, interval)
	return w.subscribe(stream)
}

func (w *WSClient) SubscribeTicker(symbol string) error {
	stream := fmt.Sprintf("%s@ticker", symbol)
	return w.subscribe(stream)
}

func (w *WSClient) SubscribeMiniTicker(symbol string) error {
	stream := fmt.Sprintf("%s@miniTicker", symbol)
	return w.subscribe(stream)
}

func (w *WSClient) subscribe(stream string) error {
	subscribeMsg := map[string]interface{}{
		"method": "SUBSCRIBE",
		"params": []string{stream},
		"id":     time.Now().Unix(),
	}

	w.mu.RLock()
	defer w.mu.RUnlock()

	if w.conn == nil {
		return fmt.Errorf("WebSocket not connected")
	}

	err := w.conn.WriteJSON(subscribeMsg)
	if err != nil {
		return err
	}

	log.Printf("Subscribing to stream: %s", stream)
	return nil
}

func (w *WSClient) readMessages() {
	for {
		select {
		case <-w.done:
			return
		default:
			w.mu.RLock()
			conn := w.conn
			w.mu.RUnlock()

			if conn == nil {
				time.Sleep(1 * time.Second)
				continue
			}

			_, message, err := conn.ReadMessage()
			if err != nil {
				log.Printf("Failed to read WebSocket message: %v", err)

				w.mu.RLock()
				currentConn := w.conn
				w.mu.RUnlock()
				if currentConn != conn {
					return
				}

				w.handleReconnect()
				return
			}

			w.handleMessage(message)
		}
	}
}

func (w *WSClient) handleMessage(message []byte) {
	var wsMsg WSMessage
	if err := json.Unmarshal(message, &wsMsg); err != nil {
		// Might be a different message format
		return
	}

	w.mu.RLock()
	ch, exists := w.subscribers[wsMsg.Stream]
	if exists {
		select {
		case ch <- wsMsg.Data:
		default:
			log.Printf("Subscriber channel is full: %s", wsMsg.Stream)
		}
	}
	w.mu.RUnlock()
}

func (w *WSClient) handleReconnect() {
	if !w.shouldReconnect() {
		return
	}

	w.reconnectMu.Lock()
	if w.reconnecting {
		w.reconnectMu.Unlock()
		return
	}
	w.reconnecting = true
	w.reconnectMu.Unlock()

	go w.reconnectLoop()
}

func (w *WSClient) reconnectLoop() {
	defer func() {
		w.reconnectMu.Lock()
		w.reconnecting = false
		w.reconnectMu.Unlock()
	}()

	backoff := 1 * time.Second
	maxBackoff := 30 * time.Second

	for {
		if !w.shouldReconnect() {
			return
		}

		select {
		case <-w.done:
			return
		default:
		}

		log.Printf("Attempting to reconnect (backoff=%s)...", backoff)
		if err := w.Connect(); err == nil {
			log.Println("WebSocket reconnected successfully")
			return
		} else {
			log.Printf("Reconnection failed: %v", err)
		}

		timer := time.NewTimer(backoff)
		select {
		case <-w.done:
			if !timer.Stop() {
				<-timer.C
			}
			return
		case <-timer.C:
		}

		if backoff < maxBackoff {
			backoff *= 2
			if backoff > maxBackoff {
				backoff = maxBackoff
			}
		}
	}
}

func (w *WSClient) AddSubscriber(stream string, bufferSize int) <-chan []byte {
	ch := make(chan []byte, bufferSize)
	w.mu.Lock()
	if existing, ok := w.subscribers[stream]; ok {
		close(existing)
	}
	w.subscribers[stream] = ch
	w.mu.Unlock()
	return ch
}

func (w *WSClient) RemoveSubscriber(stream string) {
	w.mu.Lock()
	if ch, ok := w.subscribers[stream]; ok {
		delete(w.subscribers, stream)
		close(ch)
	}
	w.mu.Unlock()
}

func (w *WSClient) shouldReconnect() bool {
	w.mu.RLock()
	defer w.mu.RUnlock()
	return w.reconnect
}

func (w *WSClient) Close() {
	w.mu.Lock()
	w.reconnect = false
	w.mu.Unlock()
	close(w.done)

	w.mu.Lock()
	defer w.mu.Unlock()

	if w.conn != nil {
		w.conn.Close()
		w.conn = nil
	}

	// Close all subscriber channels
	for stream, ch := range w.subscribers {
		close(ch)
		delete(w.subscribers, stream)
	}
}
