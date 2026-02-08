package market

import (
	"container/list"
	"sync"
	"time"
)

// LRUCache is a thread-safe LRU cache with time-based expiration
type LRUCache struct {
	capacity int
	ttl      time.Duration
	mu       sync.RWMutex
	items    map[string]*list.Element
	evictList *list.List
}

type cacheEntry struct {
	key       string
	value     interface{}
	timestamp time.Time
}

// NewLRUCache creates a new LRU cache with specified capacity and TTL
func NewLRUCache(capacity int, ttl time.Duration) *LRUCache {
	return &LRUCache{
		capacity:  capacity,
		ttl:       ttl,
		items:     make(map[string]*list.Element),
		evictList: list.New(),
	}
}

// Get retrieves a value from the cache
func (c *LRUCache) Get(key string) (interface{}, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if elem, ok := c.items[key]; ok {
		entry := elem.Value.(*cacheEntry)

		// Check if expired
		if time.Since(entry.timestamp) > c.ttl {
			c.removeElement(elem)
			return nil, false
		}

		// Move to front (most recently used)
		c.evictList.MoveToFront(elem)
		return entry.value, true
	}
	return nil, false
}

// Set adds or updates a value in the cache
func (c *LRUCache) Set(key string, value interface{}) {
	c.mu.Lock()
	defer c.mu.Unlock()

	// Update existing entry
	if elem, ok := c.items[key]; ok {
		c.evictList.MoveToFront(elem)
		entry := elem.Value.(*cacheEntry)
		entry.value = value
		entry.timestamp = time.Now()
		return
	}

	// Add new entry
	entry := &cacheEntry{
		key:       key,
		value:     value,
		timestamp: time.Now(),
	}
	elem := c.evictList.PushFront(entry)
	c.items[key] = elem

	// Evict oldest if over capacity
	if c.evictList.Len() > c.capacity {
		c.removeOldest()
	}
}

// CleanExpired removes all expired entries
func (c *LRUCache) CleanExpired() int {
	c.mu.Lock()
	defer c.mu.Unlock()

	removed := 0
	for elem := c.evictList.Back(); elem != nil; {
		entry := elem.Value.(*cacheEntry)
		if time.Since(entry.timestamp) > c.ttl {
			prev := elem.Prev()
			c.removeElement(elem)
			removed++
			elem = prev
		} else {
			break // List is ordered by access time
		}
	}
	return removed
}

// UpdateValue updates only the value of an existing entry without changing LRU order.
// Returns true if the key existed and was updated, false otherwise.
// This is optimized for high-frequency in-place updates (e.g., streaming kline ticks)
// where the entry is already hot and does not need to be promoted.
func (c *LRUCache) UpdateValue(key string, mutate func(interface{}) interface{}) bool {
	c.mu.Lock()
	defer c.mu.Unlock()

	elem, ok := c.items[key]
	if !ok {
		return false
	}
	entry := elem.Value.(*cacheEntry)
	if time.Since(entry.timestamp) > c.ttl {
		c.removeElement(elem)
		return false
	}
	entry.value = mutate(entry.value)
	return true
}

// Len returns the number of items in the cache
func (c *LRUCache) Len() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.evictList.Len()
}

// Stats returns cache statistics for monitoring
func (c *LRUCache) Stats() (size int, capacity int) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.evictList.Len(), c.capacity
}

func (c *LRUCache) removeOldest() {
	elem := c.evictList.Back()
	if elem != nil {
		c.removeElement(elem)
	}
}

func (c *LRUCache) removeElement(elem *list.Element) {
	c.evictList.Remove(elem)
	entry := elem.Value.(*cacheEntry)
	delete(c.items, entry.key)
}
