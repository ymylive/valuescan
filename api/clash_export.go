package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"nofx/logger"
	"strings"

	"github.com/gin-gonic/gin"
)

// HandleExportClashConfig Export Clash configuration as YAML
func (h *ProxyHandler) HandleExportClashConfig(c *gin.Context) {
	userID := c.GetString("user_id")

	// Get configuration
	configData, err := h.store.UserConfig().Get(userID, "clash_config")
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Configuration not found"})
		return
	}

	var config ClashConfig
	if err := json.Unmarshal([]byte(configData), &config); err != nil {
		logger.Errorf("Failed to parse Clash config: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse configuration"})
		return
	}

	// Get nodes
	nodesData, err := h.store.UserConfig().Get(userID, "clash_nodes")
	var nodes []ProxyNode
	if err == nil {
		json.Unmarshal([]byte(nodesData), &nodes)
	}

	// Generate YAML
	yaml := generateClashYAML(config, nodes)

	c.Header("Content-Type", "text/yaml")
	c.Header("Content-Disposition", "attachment; filename=clash-config.yaml")
	c.String(http.StatusOK, yaml)
}

// generateClashYAML Generate Clash YAML configuration
func generateClashYAML(config ClashConfig, nodes []ProxyNode) string {
	var sb strings.Builder

	// Basic configuration
	sb.WriteString(fmt.Sprintf("port: %d\n", config.Port))
	sb.WriteString(fmt.Sprintf("socks-port: %d\n", config.SocksPort))
	sb.WriteString(fmt.Sprintf("allow-lan: %t\n", config.AllowLan))
	sb.WriteString(fmt.Sprintf("mode: %s\n", config.Mode))
	sb.WriteString(fmt.Sprintf("log-level: %s\n", config.LogLevel))
	sb.WriteString(fmt.Sprintf("external-controller: %s\n", config.ExternalController))

	if config.Secret != "" {
		sb.WriteString(fmt.Sprintf("secret: %s\n", config.Secret))
	}

	sb.WriteString("\n")

	// Proxies section
	sb.WriteString("proxies:\n")
	if len(nodes) == 0 {
		sb.WriteString("  # No proxies configured\n")
	} else {
		for _, node := range nodes {
			sb.WriteString(generateProxyYAML(node))
		}
	}

	sb.WriteString("\n")

	// Proxy groups section
	sb.WriteString("proxy-groups:\n")
	if len(config.ProxyGroups) == 0 {
		// Use default groups if none configured
		defaultGroups := getDefaultProxyGroups()
		for _, group := range defaultGroups {
			sb.WriteString(generateProxyGroupYAML(group))
		}
	} else {
		for _, group := range config.ProxyGroups {
			sb.WriteString(generateProxyGroupYAML(group))
		}
	}

	sb.WriteString("\n")

	// Rules section
	sb.WriteString(generateDefaultRules())

	return sb.String()
}

// generateProxyYAML Generate YAML for a single proxy node
func generateProxyYAML(node ProxyNode) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("  - name: %s\n", node.Name))
	sb.WriteString(fmt.Sprintf("    type: %s\n", node.Type))
	sb.WriteString(fmt.Sprintf("    server: %s\n", node.Server))
	sb.WriteString(fmt.Sprintf("    port: %d\n", node.Port))

	// Type-specific fields
	switch node.Type {
	case "ss", "shadowsocks":
		if node.Cipher != "" {
			sb.WriteString(fmt.Sprintf("    cipher: %s\n", node.Cipher))
		}
		if node.Password != "" {
			sb.WriteString(fmt.Sprintf("    password: %s\n", node.Password))
		}
	case "vmess":
		if node.UUID != "" {
			sb.WriteString(fmt.Sprintf("    uuid: %s\n", node.UUID))
		}
		if node.AlterID > 0 {
			sb.WriteString(fmt.Sprintf("    alterId: %d\n", node.AlterID))
		}
		if node.Network != "" {
			sb.WriteString(fmt.Sprintf("    network: %s\n", node.Network))
		}
	case "trojan":
		if node.Password != "" {
			sb.WriteString(fmt.Sprintf("    password: %s\n", node.Password))
		}
	}

	// Common optional fields
	if node.TLS {
		sb.WriteString("    tls: true\n")
	}
	if node.SkipCertVerify {
		sb.WriteString("    skip-cert-verify: true\n")
	}
	if node.UDP {
		sb.WriteString("    udp: true\n")
	}

	return sb.String()
}

// generateProxyGroupYAML Generate YAML for a proxy group
func generateProxyGroupYAML(group ProxyGroup) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("  - name: %s\n", group.Name))
	sb.WriteString(fmt.Sprintf("    type: %s\n", group.Type))

	// Proxies list
	sb.WriteString("    proxies:\n")
	for _, proxy := range group.Proxies {
		sb.WriteString(fmt.Sprintf("      - %s\n", proxy))
	}

	// Type-specific fields
	switch group.Type {
	case "url-test", "fallback", "load-balance":
		if group.URL != "" {
			sb.WriteString(fmt.Sprintf("    url: %s\n", group.URL))
		}
		if group.Interval > 0 {
			sb.WriteString(fmt.Sprintf("    interval: %d\n", group.Interval))
		}
	}

	// Additional fields for specific types
	if group.Type == "url-test" && group.Tolerance > 0 {
		sb.WriteString(fmt.Sprintf("    tolerance: %d\n", group.Tolerance))
	}

	if group.Type == "load-balance" && group.Strategy != "" {
		sb.WriteString(fmt.Sprintf("    strategy: %s\n", group.Strategy))
	}

	return sb.String()
}

// generateDefaultRules Generate default Clash rules
func generateDefaultRules() string {
	var sb strings.Builder

	sb.WriteString("rules:\n")
	sb.WriteString("  # LAN\n")
	sb.WriteString("  - DOMAIN-SUFFIX,local,DIRECT\n")
	sb.WriteString("  - IP-CIDR,127.0.0.0/8,DIRECT\n")
	sb.WriteString("  - IP-CIDR,172.16.0.0/12,DIRECT\n")
	sb.WriteString("  - IP-CIDR,192.168.0.0/16,DIRECT\n")
	sb.WriteString("  - IP-CIDR,10.0.0.0/8,DIRECT\n")
	sb.WriteString("  - IP-CIDR,17.0.0.0/8,DIRECT\n")
	sb.WriteString("  - IP-CIDR,100.64.0.0/10,DIRECT\n")
	sb.WriteString("\n")
	sb.WriteString("  # China\n")
	sb.WriteString("  - GEOIP,CN,DIRECT\n")
	sb.WriteString("\n")
	sb.WriteString("  # Final\n")
	sb.WriteString("  - MATCH,Manual Select\n")

	return sb.String()
}
