package market

import (
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

type CombinedStreamsClient struct {
	conn         *websocket.Conn
	mu           sync.RWMutex
	subscribers  map[string]chan []byte
	reconnect    bool
	done         chan struct{}
	batchSize    int // Number of streams per batch subscription
	reconnectMu  sync.Mutex
	reconnecting bool
}

func NewCombinedStreamsClient(batchSize int) *CombinedStreamsClient {
	return &CombinedStreamsClient{
		subscribers: make(map[string]chan []byte),
		reconnect:   true,
		done:        make(chan struct{}),
		batchSize:   batchSize,
	}
}

func (c *CombinedStreamsClient) Connect() error {
	dialer := websocket.Dialer{
		HandshakeTimeout: 10 * time.Second,
	}

	// Combined streams use a different endpoint
	conn, _, err := dialer.Dial("wss://fstream.binance.com/stream", nil)
	if err != nil {
		return fmt.Errorf("Combined stream WebSocket connection failed: %v", err)
	}

	c.mu.Lock()
	oldConn := c.conn
	c.conn = conn
	c.mu.Unlock()

	if oldConn != nil {
		oldConn.Close()
	}

	log.Println("Combined stream WebSocket connected successfully")
	go c.readMessages()

	return nil
}

// BatchSubscribeKlines subscribes to K-lines in batches
func (c *CombinedStreamsClient) BatchSubscribeKlines(symbols []string, interval string) error {
	// Split symbols into batches
	batches := c.splitIntoBatches(symbols, c.batchSize)

	for i, batch := range batches {
		log.Printf("Subscribing batch %d, count: %d", i+1, len(batch))

		streams := make([]string, len(batch))
		for j, symbol := range batch {
			streams[j] = fmt.Sprintf("%s@kline_%s", strings.ToLower(symbol), interval)
		}

		if err := c.subscribeStreams(streams); err != nil {
			return fmt.Errorf("Batch %d subscription failed: %v", i+1, err)
		}

		// Delay between batches to avoid rate limiting
		if i < len(batches)-1 {
			time.Sleep(100 * time.Millisecond)
		}
	}

	return nil
}

// splitIntoBatches splits a slice into batches of specified size
func (c *CombinedStreamsClient) splitIntoBatches(symbols []string, batchSize int) [][]string {
	var batches [][]string

	for i := 0; i < len(symbols); i += batchSize {
		end := i + batchSize
		if end > len(symbols) {
			end = len(symbols)
		}
		batches = append(batches, symbols[i:end])
	}

	return batches
}

// subscribeStreams subscribes to multiple streams
func (c *CombinedStreamsClient) subscribeStreams(streams []string) error {
	subscribeMsg := map[string]interface{}{
		"method": "SUBSCRIBE",
		"params": streams,
		"id":     time.Now().UnixNano(),
	}

	c.mu.RLock()
	defer c.mu.RUnlock()

	if c.conn == nil {
		return fmt.Errorf("WebSocket not connected")
	}

	log.Printf("Subscribing to streams: %v", streams)
	return c.conn.WriteJSON(subscribeMsg)
}

func (c *CombinedStreamsClient) readMessages() {
	for {
		select {
		case <-c.done:
			return
		default:
			c.mu.RLock()
			conn := c.conn
			c.mu.RUnlock()

			if conn == nil {
				time.Sleep(1 * time.Second)
				continue
			}

			_, message, err := conn.ReadMessage()
			if err != nil {
				log.Printf("Failed to read combined stream message: %v", err)

				c.mu.RLock()
				currentConn := c.conn
				c.mu.RUnlock()
				if currentConn != conn {
					return
				}

				c.handleReconnect()
				return
			}

			c.handleCombinedMessage(message)
		}
	}
}

func (c *CombinedStreamsClient) handleCombinedMessage(message []byte) {
	var combinedMsg struct {
		Stream string          `json:"stream"`
		Data   json.RawMessage `json:"data"`
	}

	if err := json.Unmarshal(message, &combinedMsg); err != nil {
		log.Printf("Failed to parse combined message: %v", err)
		return
	}

	c.mu.RLock()
	ch, exists := c.subscribers[combinedMsg.Stream]
	if exists {
		select {
		case ch <- combinedMsg.Data:
		default:
			log.Printf("Subscriber channel is full: %s", combinedMsg.Stream)
		}
	}
	c.mu.RUnlock()
}

func (c *CombinedStreamsClient) AddSubscriber(stream string, bufferSize int) <-chan []byte {
	ch := make(chan []byte, bufferSize)
	c.mu.Lock()
	if existing, ok := c.subscribers[stream]; ok {
		close(existing)
	}
	c.subscribers[stream] = ch
	c.mu.Unlock()
	return ch
}

func (c *CombinedStreamsClient) handleReconnect() {
	if !c.shouldReconnect() {
		return
	}

	c.reconnectMu.Lock()
	if c.reconnecting {
		c.reconnectMu.Unlock()
		return
	}
	c.reconnecting = true
	c.reconnectMu.Unlock()

	go c.reconnectLoop()
}

func (c *CombinedStreamsClient) reconnectLoop() {
	defer func() {
		c.reconnectMu.Lock()
		c.reconnecting = false
		c.reconnectMu.Unlock()
	}()

	backoff := 1 * time.Second
	maxBackoff := 30 * time.Second

	for {
		if !c.shouldReconnect() {
			return
		}

		select {
		case <-c.done:
			return
		default:
		}

		log.Printf("Combined stream attempting to reconnect (backoff=%s)...", backoff)
		if err := c.Connect(); err == nil {
			log.Println("Combined stream reconnected successfully")
			return
		} else {
			log.Printf("Combined stream reconnection failed: %v", err)
		}

		timer := time.NewTimer(backoff)
		select {
		case <-c.done:
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

func (c *CombinedStreamsClient) shouldReconnect() bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.reconnect
}

func (c *CombinedStreamsClient) Close() {
	c.mu.Lock()
	c.reconnect = false
	c.mu.Unlock()
	close(c.done)

	c.mu.Lock()
	defer c.mu.Unlock()

	if c.conn != nil {
		c.conn.Close()
		c.conn = nil
	}

	for stream, ch := range c.subscribers {
		close(ch)
		delete(c.subscribers, stream)
	}
}
