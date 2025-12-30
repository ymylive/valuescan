// Clash 代理节点类型
export type ProxyType = 'ss' | 'ssr' | 'vmess' | 'trojan' | 'http' | 'socks5' | 'snell';

// 代理节点接口
export interface ProxyNode {
  id: string;
  name: string;
  type: ProxyType;
  server: string;
  port: number;
  cipher?: string;
  password?: string;
  uuid?: string;
  alterId?: number;
  network?: string;
  tls?: boolean;
  skipCertVerify?: boolean;
  udp?: boolean;
  delay?: number; // 延迟（毫秒）
  lastTest?: number; // 上次测速时间戳
  available?: boolean; // 是否可用
  subscriptionId?: string; // 所属订阅ID
}

// 订阅配置
export interface Subscription {
  id: string;
  name: string;
  url: string;
  enabled: boolean;
  updateInterval: number; // 更新间隔（小时）
  lastUpdate?: number; // 上次更新时间戳
  nodeCount: number; // 节点数量
  type: 'clash' | 'v2ray' | 'shadowsocks'; // 订阅类型
}

// Clash 配置
export interface ClashConfig {
  port: number;
  socksPort: number;
  allowLan: boolean;
  mode: 'rule' | 'global' | 'direct';
  logLevel: 'info' | 'warning' | 'error' | 'debug' | 'silent';
  externalController: string;
  secret: string;
  subscriptions: Subscription[];
  selectedProxy?: string; // 当前选中的代理节点ID
  autoTest: boolean; // 自动测速
  autoTestInterval: number; // 自动测速间隔（分钟）
  testUrl: string; // 测速URL
  testTimeout: number; // 测速超时（秒）
}

// 代理组
export interface ProxyGroup {
  name: string;
  type: 'select' | 'url-test' | 'fallback' | 'load-balance';
  proxies: string[];
  url?: string;
  interval?: number;
}

// Clash 统计信息
export interface ClashStats {
  uploadTotal: number;
  downloadTotal: number;
  connections: number;
  uploadSpeed: number;
  downloadSpeed: number;
}

// 节点测速结果
export interface SpeedTestResult {
  nodeId: string;
  delay: number;
  success: boolean;
  error?: string;
  timestamp: number;
}
