import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Wifi,
  Plus,
  RefreshCw,
  Trash2,
  Zap,
  CheckCircle,
  XCircle,
  Activity,
  Globe,
  Settings,
  Download,
  Upload,
} from 'lucide-react';
import { GlassCard } from '../components/Common/GlassCard';
import { Button } from '../components/Common/Button';
import { Input } from '../components/Common/Input';
import { Modal } from '../components/Common/Modal';
import { clashService } from '../services/clashService';
import { ProxyNode, Subscription, ClashStats } from '../types/clash';
import { logger } from '../services/loggerService';

const ProxyPage: React.FC = () => {
  const { t } = useTranslation();
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [nodes, setNodes] = useState<ProxyNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<ProxyNode | null>(null);
  const [stats, setStats] = useState<ClashStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [filterText, setFilterText] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'delay'>('name');

  // 新订阅表单
  const [newSubName, setNewSubName] = useState('');
  const [newSubUrl, setNewSubUrl] = useState('');
  const [newSubType, setNewSubType] = useState<'clash' | 'v2ray' | 'shadowsocks'>('clash');

  useEffect(() => {
    loadData();
    loadStats();

    // 定期更新统计信息
    const interval = setInterval(loadStats, 3000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      logger.debug('ProxyPage', '开始加载代理数据');
      const subs = clashService.getSubscriptions();
      const allNodes = await clashService.getNodes();
      const selected = await clashService.getSelectedNode();

      setSubscriptions(subs);
      setNodes(allNodes);
      setSelectedNode(selected);
      logger.info('ProxyPage', '代理数据加载成功', { subscriptions: subs.length, nodes: allNodes.length });
    } catch (error) {
      logger.error('ProxyPage', '代理数据加载失败', error as Error);
      console.error('Failed to load data:', error);
    }
  };

  const loadStats = async () => {
    try {
      const statsData = await clashService.getStats();
      setStats(statsData);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const handleAddSubscription = async () => {
    if (!newSubName || !newSubUrl) {
      alert('请填写订阅名称和 URL');
      return;
    }

    setLoading(true);
    try {
      await clashService.addSubscription(newSubName, newSubUrl, newSubType);
      loadData();
      setShowAddModal(false);
      setNewSubName('');
      setNewSubUrl('');
      setNewSubType('clash');
    } catch (error) {
      console.error('Failed to add subscription:', error);
      alert('添加订阅失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateSubscription = async (id: string) => {
    setLoading(true);
    try {
      await clashService.updateSubscription(id);
      loadData();
    } catch (error) {
      console.error('Failed to update subscription:', error);
      alert('更新订阅失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSubscription = async (id: string) => {
    if (confirm('确定要删除此订阅吗？')) {
      try {
        await clashService.deleteSubscription(id);
        await loadData();
      } catch (error) {
        console.error('Failed to delete subscription:', error);
        alert('删除订阅失败');
      }
    }
  };

  const handleTestAllNodes = async () => {
    setTesting(true);
    try {
      await clashService.testAllNodes();
      loadData();
    } catch (error) {
      console.error('Failed to test nodes:', error);
    } finally {
      setTesting(false);
    }
  };

  const handleSelectNode = async (node: ProxyNode) => {
    try {
      await clashService.selectNode(node.id);
      setSelectedNode(node);
    } catch (error) {
      console.error('Failed to select node:', error);
    }
  };

  const getFilteredAndSortedNodes = () => {
    let filtered = nodes;

    if (filterText) {
      filtered = filtered.filter(node =>
        node.name.toLowerCase().includes(filterText.toLowerCase()) ||
        node.server.toLowerCase().includes(filterText.toLowerCase())
      );
    }

    if (sortBy === 'delay') {
      filtered = [...filtered].sort((a, b) => {
        if (a.delay === undefined) return 1;
        if (b.delay === undefined) return -1;
        return a.delay - b.delay;
      });
    } else {
      filtered = [...filtered].sort((a, b) => a.name.localeCompare(b.name));
    }

    return filtered;
  };

  const getDelayColor = (delay?: number) => {
    if (delay === undefined) return 'text-gray-400';
    if (delay < 100) return 'text-green-500';
    if (delay < 300) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getDelayText = (delay?: number) => {
    if (delay === undefined) return '未测试';
    return `${delay}ms`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Wifi className="text-green-500" size={32} />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">代理节点管理</h2>
        </div>

        <div className="flex gap-3">
          <Button
            onClick={handleTestAllNodes}
            disabled={testing || nodes.length === 0}
            className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600"
          >
            <Zap className={testing ? 'animate-pulse' : ''} size={18} />
            {testing ? '测速中...' : '全部测速'}
          </Button>
          <Button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 bg-green-500 hover:bg-green-600"
          >
            <Plus size={18} />
            添加订阅
          </Button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <GlassCard className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="flex items-center gap-3">
              <Activity className="text-green-500" size={24} />
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">连接数</div>
                <div className="text-xl font-bold text-gray-900 dark:text-white">
                  {stats.connections}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Upload className="text-blue-500" size={24} />
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">上传速度</div>
                <div className="text-xl font-bold text-gray-900 dark:text-white">
                  {clashService.formatSpeed(stats.uploadSpeed)}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Download className="text-purple-500" size={24} />
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">下载速度</div>
                <div className="text-xl font-bold text-gray-900 dark:text-white">
                  {clashService.formatSpeed(stats.downloadSpeed)}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Upload className="text-cyan-500" size={24} />
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">总上传</div>
                <div className="text-xl font-bold text-gray-900 dark:text-white">
                  {clashService.formatBytes(stats.uploadTotal)}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Download className="text-indigo-500" size={24} />
              <div>
                <div className="text-sm text-gray-500 dark:text-gray-400">总下载</div>
                <div className="text-xl font-bold text-gray-900 dark:text-white">
                  {clashService.formatBytes(stats.downloadTotal)}
                </div>
              </div>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Subscriptions */}
      <GlassCard className="p-6">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">订阅列表</h3>

        {subscriptions.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            暂无订阅，点击"添加订阅"开始
          </div>
        ) : (
          <div className="space-y-3">
            {subscriptions.map(sub => (
              <div
                key={sub.id}
                className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <Globe className="text-green-500" size={20} />
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">{sub.name}</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {sub.nodeCount} 个节点 • 类型: {sub.type.toUpperCase()}
                        {sub.lastUpdate && (
                          <> • 更新于: {new Date(sub.lastUpdate).toLocaleString()}</>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    onClick={() => handleUpdateSubscription(sub.id)}
                    disabled={loading}
                    className="px-3 py-1 text-sm bg-blue-500 hover:bg-blue-600"
                  >
                    <RefreshCw className={loading ? 'animate-spin' : ''} size={16} />
                  </Button>
                  <Button
                    onClick={() => handleDeleteSubscription(sub.id)}
                    className="px-3 py-1 text-sm bg-red-500 hover:bg-red-600"
                  >
                    <Trash2 size={16} />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>

      {/* Nodes */}
      <GlassCard className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">
            节点列表 ({nodes.length})
          </h3>

          <div className="flex gap-3">
            <Input
              type="text"
              placeholder="搜索节点..."
              value={filterText}
              onChange={e => setFilterText(e.target.value)}
              className="w-64"
            />
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as 'name' | 'delay')}
              className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg"
            >
              <option value="name">按名称排序</option>
              <option value="delay">按延迟排序</option>
            </select>
          </div>
        </div>

        {nodes.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            暂无节点，请先添加订阅
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[600px] overflow-y-auto">
            {getFilteredAndSortedNodes().map(node => (
              <div
                key={node.id}
                onClick={() => handleSelectNode(node)}
                className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                  selectedNode?.id === node.id
                    ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-green-300 dark:hover:border-green-700'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="font-medium text-gray-900 dark:text-white truncate">
                      {node.name}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      {node.type.toUpperCase()} • {node.server}:{node.port}
                    </div>
                  </div>
                  {selectedNode?.id === node.id && (
                    <CheckCircle className="text-green-500 flex-shrink-0" size={20} />
                  )}
                </div>

                <div className="flex items-center justify-between">
                  <div className={`text-sm font-medium ${getDelayColor(node.delay)}`}>
                    {getDelayText(node.delay)}
                  </div>
                  {node.available !== undefined && (
                    <div className="flex items-center gap-1">
                      {node.available ? (
                        <CheckCircle className="text-green-500" size={16} />
                      ) : (
                        <XCircle className="text-red-500" size={16} />
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>

      {/* Add Subscription Modal */}
      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="添加订阅"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              订阅名称
            </label>
            <Input
              type="text"
              value={newSubName}
              onChange={e => setNewSubName(e.target.value)}
              placeholder="例如: 我的订阅"
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              订阅 URL
            </label>
            <Input
              type="text"
              value={newSubUrl}
              onChange={e => setNewSubUrl(e.target.value)}
              placeholder="https://..."
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              订阅类型
            </label>
            <select
              value={newSubType}
              onChange={e => setNewSubType(e.target.value as any)}
              className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg"
            >
              <option value="clash">Clash</option>
              <option value="v2ray">V2Ray</option>
              <option value="shadowsocks">Shadowsocks</option>
            </select>
          </div>

          <div className="flex gap-3 pt-4">
            <Button
              onClick={() => setShowAddModal(false)}
              className="flex-1 bg-gray-500 hover:bg-gray-600"
            >
              取消
            </Button>
            <Button
              onClick={handleAddSubscription}
              disabled={loading}
              className="flex-1 bg-green-500 hover:bg-green-600"
            >
              {loading ? '添加中...' : '添加'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default ProxyPage;
