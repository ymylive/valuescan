import { ProxyNode, Subscription, ClashConfig, SpeedTestResult, ClashStats } from '../types/clash';
import api from './api';

class ClashService {
  private readonly STORAGE_KEY = 'valuescan_clash_config';
  private readonly NODES_KEY = 'valuescan_clash_nodes';
  private readonly SUBSCRIPTIONS_KEY = 'valuescan_clash_subscriptions';

  // 获取 Clash 配置
  async getConfig(): Promise<ClashConfig> {
    try {
      const config = await api.get('/clash/config') as any;
      return config as ClashConfig;
    } catch (error) {
      console.error('Failed to fetch Clash config from API, using localStorage:', error);
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
      return this.getDefaultConfig();
    }
  }

  // 保存 Clash 配置
  async saveConfig(config: ClashConfig): Promise<void> {
    try {
      await api.post('/clash/config', config);
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(config));
    } catch (error) {
      console.error('Failed to save Clash config to API:', error);
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(config));
    }
  }

  // 获取默认配置
  private getDefaultConfig(): ClashConfig {
    return {
      port: 7890,
      socksPort: 7891,
      allowLan: false,
      mode: 'rule',
      logLevel: 'info',
      externalController: '127.0.0.1:9090',
      secret: '',
      subscriptions: [],
      autoTest: true,
      autoTestInterval: 30,
      testUrl: 'http://www.gstatic.com/generate_204',
      testTimeout: 5,
    };
  }

  // 获取所有订阅
  getSubscriptions(): Subscription[] {
    const stored = localStorage.getItem(this.SUBSCRIPTIONS_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
    return [];
  }

  // 保存订阅列表
  saveSubscriptions(subscriptions: Subscription[]): void {
    localStorage.setItem(this.SUBSCRIPTIONS_KEY, JSON.stringify(subscriptions));
  }

  // 添加订阅
  async addSubscription(name: string, url: string, type: 'clash' | 'v2ray' | 'shadowsocks' = 'clash'): Promise<Subscription> {
    const subscriptions = this.getSubscriptions();
    const newSub: Subscription = {
      id: Date.now().toString(),
      name,
      url,
      enabled: true,
      updateInterval: 24,
      nodeCount: 0,
      type,
    };
    subscriptions.push(newSub);
    this.saveSubscriptions(subscriptions);

    // 立即更新订阅
    await this.updateSubscription(newSub.id);

    return newSub;
  }

  // 删除订阅
  async deleteSubscription(id: string): Promise<void> {
    const subscriptions = this.getSubscriptions().filter(sub => sub.id !== id);
    this.saveSubscriptions(subscriptions);

    // 删除该订阅的所有节点
    const nodes = await this.getNodes();
    const filteredNodes = nodes.filter(node => node.subscriptionId !== id);
    await this.saveNodes(filteredNodes);
  }

  // 更新订阅
  async updateSubscription(id: string): Promise<void> {
    const subscriptions = this.getSubscriptions();
    const subscription = subscriptions.find(sub => sub.id === id);

    if (!subscription) {
      throw new Error('订阅不存在');
    }

    try {
      // 调用后端API更新订阅
      const result = await api.post('/clash/subscription/update', {
        url: subscription.url,
        type: subscription.type
      }) as any;

      const nodes = result.nodes || [];
      const groups = result.groups || [];

      // 更新节点列表
      const existingNodes = await this.getNodes();
      const filteredNodes = existingNodes.filter(node => node.subscriptionId !== id);

      // 为新节点添加ID和订阅ID
      const newNodes = nodes.map((node: any, index: number) => ({
        ...node,
        id: `${id}-${index}`,
        subscriptionId: id
      }));

      await this.saveNodes([...filteredNodes, ...newNodes]);

      // 保存策略组
      if (groups.length > 0) {
        await this.saveProxyGroups(groups);
      }

      // 更新订阅信息
      subscription.lastUpdate = Date.now();
      subscription.nodeCount = newNodes.length;
      this.saveSubscriptions(subscriptions);
    } catch (error) {
      console.error('更新订阅失败:', error);
      throw error;
    }
  }

  // 解析订阅内容
  private parseSubscription(content: string, type: string, subscriptionId: string): ProxyNode[] {
    const nodes: ProxyNode[] = [];

    try {
      if (type === 'clash') {
        // 解析 Clash 配置
        const config = this.parseYAML(content);
        if (config.proxies && Array.isArray(config.proxies)) {
          config.proxies.forEach((proxy: any, index: number) => {
            nodes.push(this.parseClashProxy(proxy, subscriptionId, index));
          });
        }
      } else if (type === 'v2ray' || type === 'shadowsocks') {
        // Base64 解码
        const decoded = atob(content);
        const lines = decoded.split('\n');

        lines.forEach((line, index) => {
          line = line.trim();
          if (line) {
            const node = this.parseProxyURL(line, subscriptionId, index);
            if (node) {
              nodes.push(node);
            }
          }
        });
      }
    } catch (error) {
      console.error('解析订阅失败:', error);
    }

    return nodes;
  }

  // 简单的 YAML 解析（仅支持基本格式）
  private parseYAML(content: string): any {
    try {
      // 尝试作为 JSON 解析
      return JSON.parse(content);
    } catch {
      // 简单的 YAML 解析
      const lines = content.split('\n');
      const result: any = { proxies: [] };
      let currentProxy: any = null;

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('- name:')) {
          if (currentProxy) {
            result.proxies.push(currentProxy);
          }
          currentProxy = {};
          currentProxy.name = trimmed.substring(7).trim().replace(/['"]/g, '');
        } else if (currentProxy && trimmed.includes(':')) {
          const [key, ...valueParts] = trimmed.split(':');
          const value = valueParts.join(':').trim().replace(/['"]/g, '');
          currentProxy[key.trim()] = value;
        }
      }

      if (currentProxy) {
        result.proxies.push(currentProxy);
      }

      return result;
    }
  }

  // 解析 Clash 代理配置
  private parseClashProxy(proxy: any, subscriptionId: string, index: number): ProxyNode {
    return {
      id: `${subscriptionId}-${index}`,
      name: proxy.name || `节点-${index}`,
      type: proxy.type || 'ss',
      server: proxy.server || '',
      port: parseInt(proxy.port) || 0,
      cipher: proxy.cipher,
      password: proxy.password,
      uuid: proxy.uuid,
      alterId: proxy.alterId,
      network: proxy.network,
      tls: proxy.tls,
      skipCertVerify: proxy['skip-cert-verify'],
      udp: proxy.udp,
      subscriptionId,
      available: undefined,
    };
  }

  // 解析代理 URL（ss://, vmess://, trojan:// 等）
  private parseProxyURL(url: string, subscriptionId: string, index: number): ProxyNode | null {
    try {
      if (url.startsWith('ss://')) {
        return this.parseShadowsocks(url, subscriptionId, index);
      } else if (url.startsWith('vmess://')) {
        return this.parseVmess(url, subscriptionId, index);
      } else if (url.startsWith('trojan://')) {
        return this.parseTrojan(url, subscriptionId, index);
      }
    } catch (error) {
      console.error('解析代理 URL 失败:', error);
    }
    return null;
  }

  // 解析 Shadowsocks URL
  private parseShadowsocks(url: string, subscriptionId: string, index: number): ProxyNode {
    const content = url.substring(5);
    const decoded = atob(content.split('#')[0]);
    const [method, rest] = decoded.split(':');
    const [password, serverPort] = rest.split('@');
    const [server, port] = serverPort.split(':');
    const name = decodeURIComponent(content.split('#')[1] || `SS-${index}`);

    return {
      id: `${subscriptionId}-${index}`,
      name,
      type: 'ss',
      server,
      port: parseInt(port),
      cipher: method,
      password,
      subscriptionId,
    };
  }

  // 解析 VMess URL
  private parseVmess(url: string, subscriptionId: string, index: number): ProxyNode {
    const content = url.substring(8);
    const decoded = JSON.parse(atob(content));

    return {
      id: `${subscriptionId}-${index}`,
      name: decoded.ps || `VMess-${index}`,
      type: 'vmess',
      server: decoded.add,
      port: parseInt(decoded.port),
      uuid: decoded.id,
      alterId: parseInt(decoded.aid),
      network: decoded.net,
      tls: decoded.tls === 'tls',
      subscriptionId,
    };
  }

  // 解析 Trojan URL
  private parseTrojan(url: string, subscriptionId: string, index: number): ProxyNode {
    const content = url.substring(9);
    const [password, rest] = content.split('@');
    const [serverPort, name] = rest.split('#');
    const [server, port] = serverPort.split(':');

    return {
      id: `${subscriptionId}-${index}`,
      name: decodeURIComponent(name || `Trojan-${index}`),
      type: 'trojan',
      server,
      port: parseInt(port),
      password,
      subscriptionId,
    };
  }

  // 获取所有节点
  async getNodes(): Promise<ProxyNode[]> {
    try {
      const nodes = await api.get('/clash/nodes') as any;
      return nodes as ProxyNode[];
    } catch (error) {
      console.error('Failed to fetch nodes from API, using localStorage:', error);
      const stored = localStorage.getItem(this.NODES_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
      return [];
    }
  }

  // 保存节点列表
  async saveNodes(nodes: ProxyNode[]): Promise<void> {
    try {
      await api.post('/clash/nodes', nodes);
      localStorage.setItem(this.NODES_KEY, JSON.stringify(nodes));
    } catch (error) {
      console.error('Failed to save nodes to API:', error);
      localStorage.setItem(this.NODES_KEY, JSON.stringify(nodes));
    }
  }

  // 测速单个节点
  async testNode(nodeId: string): Promise<SpeedTestResult> {
    const startTime = Date.now();

    try {
      // 调用后端 API 进行实际测速
      const result = await api.post('/clash/test-node', { nodeId }) as any;
      const testResult = result as SpeedTestResult;

      // 更新节点延迟信息
      const nodes = await this.getNodes();
      const node = nodes.find(n => n.id === nodeId);
      if (node && testResult.success) {
        node.delay = testResult.delay;
        node.lastTest = Date.now();
        node.available = true;
        await this.saveNodes(nodes);
      }

      return testResult;
    } catch (error) {
      return {
        nodeId,
        delay: -1,
        success: false,
        error: error instanceof Error ? error.message : '测速失败',
        timestamp: Date.now(),
      };
    }
  }

  // 批量测速
  async testAllNodes(): Promise<SpeedTestResult[]> {
    const nodes = await this.getNodes();
    const results: SpeedTestResult[] = [];

    for (const node of nodes) {
      const result = await this.testNode(node.id);
      results.push(result);
    }

    return results;
  }

  // 选择节点
  async selectNode(nodeId: string): Promise<void> {
    const config = await this.getConfig();
    config.selectedProxy = nodeId;
    await this.saveConfig(config);
  }

  // 获取当前选中的节点
  async getSelectedNode(): Promise<ProxyNode | null> {
    const config = await this.getConfig();
    if (!config.selectedProxy) {
      return null;
    }
    const nodes = await this.getNodes();
    return nodes.find(node => node.id === config.selectedProxy) || null;
  }

  // 获取统计信息
  async getStats(): Promise<ClashStats> {
    try {
      const stats = await api.get('/clash/stats') as any;
      return stats as ClashStats;
    } catch (error) {
      console.error('Failed to fetch stats from API:', error);
      // 返回默认值
      return {
        uploadTotal: 0,
        downloadTotal: 0,
        connections: 0,
        uploadSpeed: 0,
        downloadSpeed: 0,
      };
    }
  }

  // 格式化流量
  formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }

  // 格式化速度
  formatSpeed(bytesPerSecond: number): string {
    return this.formatBytes(bytesPerSecond) + '/s';
  }

  // ==================== 策略组管理 ====================

  // 获取策略组列表
  async getProxyGroups(): Promise<any[]> {
    try {
      const groups = await api.get('/clash/groups') as any;
      return groups || [];
    } catch (error) {
      console.error('Failed to fetch proxy groups:', error);
      return [];
    }
  }

  // 保存策略组列表
  async saveProxyGroups(groups: any[]): Promise<void> {
    try {
      await api.post('/clash/groups', { groups });
    } catch (error) {
      console.error('Failed to save proxy groups:', error);
      throw error;
    }
  }

  // 自动生成策略组
  async generateProxyGroups(): Promise<any[]> {
    try {
      const result = await api.post('/clash/groups/generate', {}) as any;
      return result.groups || [];
    } catch (error) {
      console.error('Failed to generate proxy groups:', error);
      throw error;
    }
  }

  // 导出 Clash 配置
  async exportClashConfig(): Promise<string> {
    try {
      const response = await fetch('/api/clash/export', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      });

      if (!response.ok) {
        throw new Error('导出失败');
      }

      return await response.text();
    } catch (error) {
      console.error('Failed to export Clash config:', error);
      throw error;
    }
  }
}

export const clashService = new ClashService();
