# Clash 策略组功能实现文档

## 更新时间
2025-12-31

## 已完成的工作

### 1. 类型定义 ✅

**文件**: `web/src/types/clash.ts`

已添加完整的策略组类型定义:

```typescript
// 策略组类型
export type ProxyGroupType = 'select' | 'url-test' | 'fallback' | 'load-balance';

// 代理组接口
export interface ProxyGroup {
  id: string;
  name: string;
  type: ProxyGroupType;
  proxies: string[]; // 节点ID列表
  url?: string; // 测试URL (url-test, fallback)
  interval?: number; // 测试间隔(秒) (url-test, fallback)
  tolerance?: number; // 容差(ms) (url-test)
  strategy?: 'consistent-hashing' | 'round-robin'; // 负载均衡策略
}

// ClashConfig 已添加 proxyGroups 字段
export interface ClashConfig {
  // ... 其他字段
  proxyGroups?: ProxyGroup[]; // 策略组列表
}
```

### 2. UI 组件 ✅

**已创建的组件**:

1. **ProxyGroupCard** (`web/src/components/Proxy/ProxyGroupCard.tsx`)
   - 显示策略组信息
   - 支持编辑和删除操作
   - 不同类型的策略组有不同的颜色标识

2. **ProxyGroupModal** (`web/src/components/Proxy/ProxyGroupModal.tsx`)
   - 添加/编辑策略组
   - 支持所有4种策略组类型
   - 动态显示不同类型的配置选项
   - 多选节点功能

---

## 策略组类型说明

### 1. Select (手动选择)
- **用途**: 手动切换节点
- **配置**: 只需选择节点列表
- **适用场景**: 需要手动控制使用哪个节点

### 2. URL-Test (自动测速)
- **用途**: 自动选择延迟最低的节点
- **配置**:
  - 测试URL
  - 测试间隔(秒)
  - 容差(毫秒)
- **适用场景**: 自动选择最快的节点

### 3. Fallback (故障转移)
- **用途**: 按顺序选择第一个可用节点
- **配置**:
  - 测试URL
  - 测试间隔(秒)
- **适用场景**: 主节点故障时自动切换到备用节点

### 4. Load-Balance (负载均衡)
- **用途**: 分散请求到多个节点
- **配置**:
  - 负载均衡策略
- **适用场景**: 分散流量,提高稳定性

---

## 待完成的工作

### 1. 集成到 ProxyPage

需要在 `web/src/pages/ProxyPage.tsx` 中:

```typescript
// 添加状态
const [proxyGroups, setProxyGroups] = useState<ProxyGroup[]>([]);
const [showGroupModal, setShowGroupModal] = useState(false);
const [editingGroup, setEditingGroup] = useState<ProxyGroup | undefined>();

// 添加处理函数
const handleSaveGroup = (group: ProxyGroup) => {
  // 保存策略组逻辑
};

const handleDeleteGroup = (groupId: string) => {
  // 删除策略组逻辑
};
```

### 2. 更新 clashService

需要在 `web/src/services/clashService.ts` 中添加:

```typescript
// 获取策略组
async getProxyGroups(): Promise<ProxyGroup[]> {
  const config = await this.getConfig();
  return config.proxyGroups || [];
}

// 保存策略组
async saveProxyGroups(groups: ProxyGroup[]): Promise<void> {
  const config = await this.getConfig();
  config.proxyGroups = groups;
  await this.saveConfig(config);
}
```

### 3. 后端 API 支持

后端已有 `/api/clash/config` 端点,支持读写配置,无需额外修改。

---

## 使用示例

### 创建自动测速策略组

```json
{
  "id": "1",
  "name": "自动选择",
  "type": "url-test",
  "proxies": ["node-1", "node-2", "node-3"],
  "url": "http://www.gstatic.com/generate_204",
  "interval": 300,
  "tolerance": 150
}
```

### 创建故障转移策略组

```json
{
  "id": "2",
  "name": "故障转移",
  "type": "fallback",
  "proxies": ["node-1", "node-2", "node-3"],
  "url": "http://www.gstatic.com/generate_204",
  "interval": 300
}
```

---

## 下一步操作

1. 在 ProxyPage 中导入组件
2. 添加策略组管理UI
3. 实现策略组的增删改查
4. 测试所有策略组类型

## 文件清单

- ✅ `web/src/types/clash.ts` - 类型定义
- ✅ `web/src/components/Proxy/ProxyGroupCard.tsx` - 策略组卡片
- ✅ `web/src/components/Proxy/ProxyGroupModal.tsx` - 策略组编辑
- ⏳ `web/src/pages/ProxyPage.tsx` - 待集成
- ⏳ `web/src/services/clashService.ts` - 待添加方法
