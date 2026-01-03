package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"nofx/logger"
	"nofx/store"

	"github.com/gin-gonic/gin"
)

// ProxyHandler Clash proxy management handler
type ProxyHandler struct {
	store *store.Store
}

// NewProxyHandler Create proxy handler
func NewProxyHandler(st *store.Store) *ProxyHandler {
	return &ProxyHandler{
		store: st,
	}
}

// ProxyNode Proxy node structure
type ProxyNode struct {
	ID             string `json:"id"`
	Name           string `json:"name"`
	Type           string `json:"type"`
	Server         string `json:"server"`
	Port           int    `json:"port"`
	Cipher         string `json:"cipher,omitempty"`
	Password       string `json:"password,omitempty"`
	UUID           string `json:"uuid,omitempty"`
	AlterID        int    `json:"alterId,omitempty"`
	Network        string `json:"network,omitempty"`
	TLS            bool   `json:"tls,omitempty"`
	SkipCertVerify bool   `json:"skipCertVerify,omitempty"`
	UDP            bool   `json:"udp,omitempty"`
	Delay          int    `json:"delay,omitempty"`
	LastTest       int64  `json:"lastTest,omitempty"`
	Available      *bool  `json:"available,omitempty"`
	SubscriptionID string `json:"subscriptionId,omitempty"`
}

// Subscription Subscription structure
type Subscription struct {
	ID             string `json:"id"`
	Name           string `json:"name"`
	URL            string `json:"url"`
	Enabled        bool   `json:"enabled"`
	UpdateInterval int    `json:"updateInterval"`
	LastUpdate     int64  `json:"lastUpdate,omitempty"`
	NodeCount      int    `json:"nodeCount"`
	Type           string `json:"type"`
}

// ProxyGroup Clash proxy group structure
type ProxyGroup struct {
	ID        string   `json:"id"`
	Name      string   `json:"name"`
	Type      string   `json:"type"` // select, url-test, fallback, load-balance
	Proxies   []string `json:"proxies"`
	URL       string   `json:"url,omitempty"`
	Interval  int      `json:"interval,omitempty"`
	Tolerance int      `json:"tolerance,omitempty"`
	Strategy  string   `json:"strategy,omitempty"` // consistent-hashing, round-robin
}

// ClashConfig Clash configuration structure
type ClashConfig struct {
	Port               int            `json:"port"`
	SocksPort          int            `json:"socksPort"`
	AllowLan           bool           `json:"allowLan"`
	Mode               string         `json:"mode"`
	LogLevel           string         `json:"logLevel"`
	ExternalController string         `json:"externalController"`
	Secret             string         `json:"secret"`
	Subscriptions      []Subscription `json:"subscriptions"`
	ProxyGroups        []ProxyGroup   `json:"proxyGroups"`
	SelectedProxy      string         `json:"selectedProxy,omitempty"`
	AutoTest           bool           `json:"autoTest"`
	AutoTestInterval   int            `json:"autoTestInterval"`
	TestURL            string         `json:"testUrl"`
	TestTimeout        int            `json:"testTimeout"`
}

// HandleGetConfig Get Clash configuration
func (h *ProxyHandler) HandleGetConfig(c *gin.Context) {
	userID := c.GetString("user_id")

	// Get configuration from database
	configData, err := h.store.UserConfig().Get(userID, "clash_config")
	if err != nil {
		// Return default configuration with default proxy groups
		defaultConfig := ClashConfig{
			Port:               7890,
			SocksPort:          7891,
			AllowLan:           false,
			Mode:               "rule",
			LogLevel:           "info",
			ExternalController: "127.0.0.1:9090",
			Secret:             "",
			Subscriptions:      []Subscription{},
			ProxyGroups:        getDefaultProxyGroups(),
			AutoTest:           true,
			AutoTestInterval:   30,
			TestURL:            "http://www.gstatic.com/generate_204",
			TestTimeout:        5,
		}
		c.JSON(http.StatusOK, defaultConfig)
		return
	}

	var config ClashConfig
	if err := json.Unmarshal([]byte(configData), &config); err != nil {
		logger.Errorf("Failed to parse Clash config: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse configuration"})
		return
	}

	c.JSON(http.StatusOK, config)
}

// HandleSaveConfig Save Clash configuration
func (h *ProxyHandler) HandleSaveConfig(c *gin.Context) {
	userID := c.GetString("user_id")

	var config ClashConfig
	if err := c.ShouldBindJSON(&config); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Serialize configuration
	configData, err := json.Marshal(config)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to serialize configuration"})
		return
	}

	// Save to database
	if err := h.store.UserConfig().Set(userID, "clash_config", string(configData)); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save configuration"})
		return
	}

	logger.Infof("✓ Saved Clash config for user %s", userID)
	c.JSON(http.StatusOK, gin.H{"message": "Configuration saved successfully"})
}

// HandleGetNodes Get all proxy nodes
func (h *ProxyHandler) HandleGetNodes(c *gin.Context) {
	userID := c.GetString("user_id")

	// Get nodes from database
	nodesData, err := h.store.UserConfig().Get(userID, "clash_nodes")
	if err != nil {
		c.JSON(http.StatusOK, []ProxyNode{})
		return
	}

	var nodes []ProxyNode
	if err := json.Unmarshal([]byte(nodesData), &nodes); err != nil {
		logger.Errorf("Failed to parse Clash nodes: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse nodes"})
		return
	}

	c.JSON(http.StatusOK, nodes)
}

// HandleSaveNodes Save proxy nodes
func (h *ProxyHandler) HandleSaveNodes(c *gin.Context) {
	userID := c.GetString("user_id")

	var nodes []ProxyNode
	if err := c.ShouldBindJSON(&nodes); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Serialize nodes
	nodesData, err := json.Marshal(nodes)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to serialize nodes"})
		return
	}

	// Save to database
	if err := h.store.UserConfig().Set(userID, "clash_nodes", string(nodesData)); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save nodes"})
		return
	}

	logger.Infof("✓ Saved %d Clash nodes for user %s", len(nodes), userID)
	c.JSON(http.StatusOK, gin.H{"message": "Nodes saved successfully", "count": len(nodes)})
}

// HandleTestNode Test single node speed
func (h *ProxyHandler) HandleTestNode(c *gin.Context) {
	nodeID := c.Param("id")

	// TODO: Implement actual speed test logic
	// For now, return mock data
	delay := 100 + (len(nodeID) % 200) // Mock delay based on ID

	c.JSON(http.StatusOK, gin.H{
		"nodeId":    nodeID,
		"delay":     delay,
		"success":   true,
		"timestamp": c.Request.Context().Value("time"),
	})
}

// HandleTestAllNodes Test all nodes speed
func (h *ProxyHandler) HandleTestAllNodes(c *gin.Context) {
	userID := c.GetString("user_id")

	// Get nodes from database
	nodesData, err := h.store.GetUserConfig(userID, "clash_nodes")
	if err != nil {
		c.JSON(http.StatusOK, []interface{}{})
		return
	}

	var nodes []ProxyNode
	if err := json.Unmarshal([]byte(nodesData), &nodes); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse nodes"})
		return
	}

	// TODO: Implement actual batch speed test logic
	// For now, return mock results
	results := make([]map[string]interface{}, len(nodes))
	for i, node := range nodes {
		delay := 100 + (i * 50 % 300)
		results[i] = map[string]interface{}{
			"nodeId":    node.ID,
			"delay":     delay,
			"success":   true,
			"timestamp": c.Request.Context().Value("time"),
		}
	}

	c.JSON(http.StatusOK, results)
}

// HandleGetStats Get Clash statistics
func (h *ProxyHandler) HandleGetStats(c *gin.Context) {
	// TODO: Implement actual Clash stats retrieval
	// For now, return mock data
	c.JSON(http.StatusOK, gin.H{
		"uploadTotal":   1024 * 1024 * 100, // 100MB
		"downloadTotal": 1024 * 1024 * 500, // 500MB
		"connections":   42,
		"uploadSpeed":   1024 * 50,  // 50KB/s
		"downloadSpeed": 1024 * 200, // 200KB/s
	})
}

// getDefaultProxyGroups Get default proxy groups
func getDefaultProxyGroups() []ProxyGroup {
	return []ProxyGroup{
		{
			ID:       "auto",
			Name:     "Auto Select",
			Type:     "url-test",
			Proxies:  []string{"DIRECT"},
			URL:      "http://www.gstatic.com/generate_204",
			Interval: 300,
		},
		{
			ID:       "fallback",
			Name:     "Fallback",
			Type:     "fallback",
			Proxies:  []string{"DIRECT"},
			URL:      "http://www.gstatic.com/generate_204",
			Interval: 300,
		},
		{
			ID:      "select",
			Name:    "Manual Select",
			Type:    "select",
			Proxies: []string{"DIRECT", "Auto Select", "Fallback"},
		},
		{
			ID:       "loadbalance",
			Name:     "Load Balance",
			Type:     "load-balance",
			Proxies:  []string{"DIRECT"},
			URL:      "http://www.gstatic.com/generate_204",
			Interval: 300,
			Strategy: "consistent-hashing",
		},
	}
}

// HandleGetProxyGroups Get all proxy groups
func (h *ProxyHandler) HandleGetProxyGroups(c *gin.Context) {
	userID := c.GetString("user_id")

	// Get configuration from database
	configData, err := h.store.UserConfig().Get(userID, "clash_config")
	if err != nil {
		c.JSON(http.StatusOK, getDefaultProxyGroups())
		return
	}

	var config ClashConfig
	if err := json.Unmarshal([]byte(configData), &config); err != nil {
		logger.Errorf("Failed to parse Clash config: %v", err)
		c.JSON(http.StatusOK, getDefaultProxyGroups())
		return
	}

	if len(config.ProxyGroups) == 0 {
		c.JSON(http.StatusOK, getDefaultProxyGroups())
		return
	}

	c.JSON(http.StatusOK, config.ProxyGroups)
}
