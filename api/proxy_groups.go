package api

import (
	"encoding/json"
	"net/http"
	"nofx/logger"

	"github.com/gin-gonic/gin"
)

// HandleSaveProxyGroups Save proxy groups
func (h *ProxyHandler) HandleSaveProxyGroups(c *gin.Context) {
	userID := c.GetString("user_id")

	var groups []ProxyGroup
	if err := c.ShouldBindJSON(&groups); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Get existing configuration
	configData, err := h.store.UserConfig().Get(userID, "clash_config")
	var config ClashConfig
	if err != nil {
		// Create new config with default values
		config = ClashConfig{
			Port:               7890,
			SocksPort:          7891,
			AllowLan:           false,
			Mode:               "rule",
			LogLevel:           "info",
			ExternalController: "127.0.0.1:9090",
			Secret:             "",
			Subscriptions:      []Subscription{},
			AutoTest:           true,
			AutoTestInterval:   30,
			TestURL:            "http://www.gstatic.com/generate_204",
			TestTimeout:        5,
		}
	} else {
		if err := json.Unmarshal([]byte(configData), &config); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse configuration"})
			return
		}
	}

	// Update proxy groups
	config.ProxyGroups = groups

	// Save configuration
	newConfigData, err := json.Marshal(config)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to serialize configuration"})
		return
	}

	if err := h.store.UserConfig().Set(userID, "clash_config", string(newConfigData)); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save configuration"})
		return
	}

	logger.Infof("✓ Saved %d proxy groups for user %s", len(groups), userID)
	c.JSON(http.StatusOK, gin.H{"message": "Proxy groups saved successfully", "count": len(groups)})
}

// HandleUpdateProxyGroup Update a single proxy group
func (h *ProxyHandler) HandleUpdateProxyGroup(c *gin.Context) {
	userID := c.GetString("user_id")
	groupID := c.Param("id")

	var updatedGroup ProxyGroup
	if err := c.ShouldBindJSON(&updatedGroup); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Get existing configuration
	configData, err := h.store.UserConfig().Get(userID, "clash_config")
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Configuration not found"})
		return
	}

	var config ClashConfig
	if err := json.Unmarshal([]byte(configData), &config); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse configuration"})
		return
	}

	// Find and update the group
	found := false
	for i, group := range config.ProxyGroups {
		if group.ID == groupID {
			config.ProxyGroups[i] = updatedGroup
			found = true
			break
		}
	}

	if !found {
		c.JSON(http.StatusNotFound, gin.H{"error": "Proxy group not found"})
		return
	}

	// Save configuration
	newConfigData, err := json.Marshal(config)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to serialize configuration"})
		return
	}

	if err := h.store.UserConfig().Set(userID, "clash_config", string(newConfigData)); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save configuration"})
		return
	}

	logger.Infof("✓ Updated proxy group %s for user %s", groupID, userID)
	c.JSON(http.StatusOK, gin.H{"message": "Proxy group updated successfully"})
}

// HandleDeleteProxyGroup Delete a proxy group
func (h *ProxyHandler) HandleDeleteProxyGroup(c *gin.Context) {
	userID := c.GetString("user_id")
	groupID := c.Param("id")

	// Get existing configuration
	configData, err := h.store.UserConfig().Get(userID, "clash_config")
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Configuration not found"})
		return
	}

	var config ClashConfig
	if err := json.Unmarshal([]byte(configData), &config); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse configuration"})
		return
	}

	// Find and remove the group
	found := false
	newGroups := []ProxyGroup{}
	for _, group := range config.ProxyGroups {
		if group.ID != groupID {
			newGroups = append(newGroups, group)
		} else {
			found = true
		}
	}

	if !found {
		c.JSON(http.StatusNotFound, gin.H{"error": "Proxy group not found"})
		return
	}

	config.ProxyGroups = newGroups

	// Save configuration
	newConfigData, err := json.Marshal(config)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to serialize configuration"})
		return
	}

	if err := h.store.UserConfig().Set(userID, "clash_config", string(newConfigData)); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save configuration"})
		return
	}

	logger.Infof("✓ Deleted proxy group %s for user %s", groupID, userID)
	c.JSON(http.StatusOK, gin.H{"message": "Proxy group deleted successfully"})
}

// HandleGenerateProxyGroups Auto-generate proxy groups based on nodes
func (h *ProxyHandler) HandleGenerateProxyGroups(c *gin.Context) {
	userID := c.GetString("user_id")

	// Get nodes from database
	nodesData, err := h.store.UserConfig().Get(userID, "clash_nodes")
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"groups": getDefaultProxyGroups()})
		return
	}

	var nodes []ProxyNode
	if err := json.Unmarshal([]byte(nodesData), &nodes); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse nodes"})
		return
	}

	// Generate proxy groups based on nodes
	groups := generateProxyGroupsFromNodes(nodes)

	c.JSON(http.StatusOK, gin.H{"groups": groups, "count": len(groups)})
}

// generateProxyGroupsFromNodes Generate proxy groups from node list
func generateProxyGroupsFromNodes(nodes []ProxyNode) []ProxyGroup {
	if len(nodes) == 0 {
		return getDefaultProxyGroups()
	}

	// Collect all node names
	nodeNames := []string{}
	for _, node := range nodes {
		nodeNames = append(nodeNames, node.Name)
	}

	// Create proxy groups
	groups := []ProxyGroup{
		{
			ID:       "auto",
			Name:     "Auto Select",
			Type:     "url-test",
			Proxies:  append([]string{"DIRECT"}, nodeNames...),
			URL:      "http://www.gstatic.com/generate_204",
			Interval: 300,
		},
		{
			ID:       "fallback",
			Name:     "Fallback",
			Type:     "fallback",
			Proxies:  append([]string{"DIRECT"}, nodeNames...),
			URL:      "http://www.gstatic.com/generate_204",
			Interval: 300,
		},
		{
			ID:      "select",
			Name:    "Manual Select",
			Type:    "select",
			Proxies: append([]string{"DIRECT", "Auto Select", "Fallback"}, nodeNames...),
		},
		{
			ID:       "loadbalance",
			Name:     "Load Balance",
			Type:     "load-balance",
			Proxies:  nodeNames,
			URL:      "http://www.gstatic.com/generate_204",
			Interval: 300,
			Strategy: "consistent-hashing",
		},
	}

	return groups
}
