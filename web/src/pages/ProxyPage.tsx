import React from 'react';
import { ExternalLink, Wifi, Copy, CheckCircle, AlertCircle, RefreshCw, Plus, Link as LinkIcon } from 'lucide-react';
import { GlassCard } from '../components/Common/GlassCard';
import { Button } from '../components/Common/Button';

const SUBSCRIPTIONS_KEY = 'valuescan_proxy_subscriptions';

interface ClashServiceStatus {
  running: boolean;
  port: number;
  api_url: string;
  error?: string;
}

interface Subscription {
  id: string;
  name: string;
  url: string;
  type: 'clash' | 'base64';
}

const ProxyPage: React.FC = () => {
  const [copied, setCopied] = React.useState(false);
  const [serviceStatus, setServiceStatus] = React.useState<ClashServiceStatus | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [checking, setChecking] = React.useState(true);
  const [showSubscriptionModal, setShowSubscriptionModal] = React.useState(false);
  const [subscriptionUrl, setSubscriptionUrl] = React.useState('');
  const [subscriptionType, setSubscriptionType] = React.useState<'clash' | 'base64'>('clash');
  const [subscriptionName, setSubscriptionName] = React.useState('');
  const [savedSubscriptions, setSavedSubscriptions] = React.useState<Subscription[]>([]);
  const [selectedSubscriptionId, setSelectedSubscriptionId] = React.useState('');
  const [updating, setUpdating] = React.useState(false);
  const [nodeCount, setNodeCount] = React.useState(0);

  const clashApiUrl = `${window.location.protocol}//${window.location.host}/clash-api`;
  const metacubexUrl = 'https://metacubex.github.io/metacubexd/';

  // 检查 Clash 服务状态
  const checkServiceStatus = async () => {
    setChecking(true);
    try {
      const response = await fetch('/api/clash/service/status');
      const data = await response.json();
      setServiceStatus(data);
    } catch (error) {
      console.error('Failed to check Clash service status:', error);
      setServiceStatus({ running: false, port: 9090, api_url: 'http://127.0.0.1:9090', error: '无法连接到后端 API' });
    } finally {
      setChecking(false);
    }
  };

  // 启动 Clash 服务
  const startService = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/clash/service/start', { method: 'POST' });
      const data = await response.json();

      if (response.ok) {
        alert(data.message || 'Clash 服务启动成功');
        await checkServiceStatus();
      } else {
        alert(data.error || 'Clash 服务启动失败');
      }
    } catch (error) {
      console.error('Failed to start Clash service:', error);
      alert('启动 Clash 服务失败');
    } finally {
      setLoading(false);
    }
  };

  // 页面加载时检查服务状态
  React.useEffect(() => {
    checkServiceStatus();
    // 每 10 秒自动检查一次
    const interval = setInterval(checkServiceStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  React.useEffect(() => {
    try {
      const stored = localStorage.getItem(SUBSCRIPTIONS_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as Subscription[];
        setSavedSubscriptions(parsed);
      }
    } catch (error) {
      console.error('Failed to load subscriptions from localStorage:', error);
    }
  }, []);

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(clashApiUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleOpenMetaCubeX = () => {
    window.open(metacubexUrl, '_blank');
  };

  const handleSelectSubscription = (id: string) => {
    setSelectedSubscriptionId(id);
    const selected = savedSubscriptions.find((sub) => sub.id === id);
    if (selected) {
      setSubscriptionName(selected.name);
      setSubscriptionUrl(selected.url);
      setSubscriptionType(selected.type);
    }
  };

  const handleImportSubscription = () => {
    if (!subscriptionUrl.trim()) {
      alert('请输入订阅链接');
      return;
    }

    const name = subscriptionName.trim() || `订阅-${savedSubscriptions.length + 1}`;
    const url = subscriptionUrl.trim();
    const existingIndex = savedSubscriptions.findIndex((sub) => sub.url === url);
    const nextSubscriptions = [...savedSubscriptions];

    if (existingIndex >= 0) {
      const existing = nextSubscriptions[existingIndex];
      nextSubscriptions[existingIndex] = { ...existing, name, url, type: subscriptionType };
      setSelectedSubscriptionId(existing.id);
    } else {
      const newSub: Subscription = {
        id: Date.now().toString(),
        name,
        url,
        type: subscriptionType,
      };
      nextSubscriptions.unshift(newSub);
      setSelectedSubscriptionId(newSub.id);
    }

    setSavedSubscriptions(nextSubscriptions);
    localStorage.setItem(SUBSCRIPTIONS_KEY, JSON.stringify(nextSubscriptions));
    alert('订阅已导入');
  };

  // 更新订阅
  const handleUpdateSubscription = async () => {
    if (!subscriptionUrl.trim()) {
      alert('请输入订阅链接');
      return;
    }

    setUpdating(true);
    const trimmedUrl = subscriptionUrl.trim();
    const trimmedName = subscriptionName.trim();

    try {
      const response = await fetch('/api/clash/subscription/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: trimmedUrl,
          type: subscriptionType,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setNodeCount(data.count || 0);
        alert(`订阅更新成功！解析到 ${data.count} 个节点`);

        if (selectedSubscriptionId) {
          const updatedSubscriptions = savedSubscriptions.map((sub) => (
            sub.id === selectedSubscriptionId
              ? {
                ...sub,
                name: trimmedName || sub.name,
                url: trimmedUrl,
                type: subscriptionType,
              }
              : sub
          ));
          setSavedSubscriptions(updatedSubscriptions);
          localStorage.setItem(SUBSCRIPTIONS_KEY, JSON.stringify(updatedSubscriptions));
        }

        setShowSubscriptionModal(false);
        setSubscriptionUrl('');
        setSubscriptionName('');
      } else {
        alert(data.error || '订阅更新失败');
      }
    } catch (error) {
      console.error('Failed to update subscription:', error);
      alert('订阅更新失败');
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Wifi className="text-green-500" size={32} />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">代理节点管理</h2>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => setShowSubscriptionModal(true)}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700"
          >
            <LinkIcon size={18} />
            订阅管理
          </Button>
          <Button
            onClick={checkServiceStatus}
            disabled={checking}
            className="flex items-center gap-2"
          >
            <RefreshCw size={18} className={checking ? 'animate-spin' : ''} />
            刷新状态
          </Button>
        </div>
      </div>

      {/* Service Status Alert */}
      {serviceStatus && !serviceStatus.running && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" size={20} />
            <div className="flex-1">
              <h3 className="font-semibold text-yellow-800 dark:text-yellow-200 mb-1">
                Clash 服务未运行
              </h3>
              <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-3">
                检测到 Clash 服务（端口 9090）未启动。请先启动 Clash/Mihomo 服务才能使用 MetaCubeX 管理界面。
              </p>
              <div className="flex gap-2">
                <Button
                  onClick={startService}
                  disabled={loading}
                  className="bg-yellow-600 hover:bg-yellow-700 text-white text-sm"
                >
                  {loading ? '启动中...' : '尝试启动服务'}
                </Button>
                <Button
                  onClick={checkServiceStatus}
                  disabled={checking}
                  className="bg-gray-600 hover:bg-gray-700 text-white text-sm"
                >
                  重新检查
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Service Running Status */}
      {serviceStatus && serviceStatus.running && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
            <div>
              <h3 className="font-semibold text-green-800 dark:text-green-200">
                Clash 服务运行中
              </h3>
              <p className="text-sm text-green-700 dark:text-green-300">
                服务正常运行在端口 {serviceStatus.port}，可以使用 MetaCubeX 进行管理
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Instructions */}
      <GlassCard className="p-8">
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <Wifi className="text-green-500" size={48} />
            <div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                使用 MetaCubeX 管理 Clash 代理
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                MetaCubeX 是 Mihomo (Clash Meta) 的官方 Web 管理界面
              </p>
            </div>
          </div>

          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-4">
              使用步骤：
            </h4>

            <div className="space-y-4">
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold">
                  1
                </div>
                <div className="flex-1">
                  <p className="text-gray-900 dark:text-white font-medium mb-2">
                    复制 Clash API 地址
                  </p>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={clashApiUrl}
                      readOnly
                      className="flex-1 px-4 py-2 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white"
                    />
                    <Button
                      onClick={handleCopyUrl}
                      className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600"
                    >
                      {copied ? <CheckCircle size={18} /> : <Copy size={18} />}
                      {copied ? '已复制' : '复制'}
                    </Button>
                  </div>
                </div>
              </div>

              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold">
                  2
                </div>
                <div className="flex-1">
                  <p className="text-gray-900 dark:text-white font-medium mb-2">
                    打开 MetaCubeX 管理界面
                  </p>
                  <Button
                    onClick={handleOpenMetaCubeX}
                    className="flex items-center gap-2 bg-green-500 hover:bg-green-600"
                  >
                    <ExternalLink size={18} />
                    打开 MetaCubeX
                  </Button>
                </div>
              </div>

              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold">
                  3
                </div>
                <div className="flex-1">
                  <p className="text-gray-900 dark:text-white font-medium mb-2">
                    在 MetaCubeX 中配置连接
                  </p>
                  <ul className="list-disc list-inside text-gray-600 dark:text-gray-400 space-y-1">
                    <li>点击左上角的设置图标</li>
                    <li>在 "Backend URL" 中粘贴上面复制的 API 地址</li>
                    <li>点击 "Add" 添加连接</li>
                    <li>开始管理您的代理节点</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              <strong>提示：</strong> MetaCubeX 是纯前端应用，所有数据都保存在您的浏览器中，非常安全。
            </p>
          </div>
        </div>
      </GlassCard>

      {/* Subscription Modal */}
      {showSubscriptionModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                  订阅管理
                </h3>
                <button
                  onClick={() => setShowSubscriptionModal(false)}
                  className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-4">
                {/* Imported Subscriptions */}
                {savedSubscriptions.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      已导入订阅
                    </label>
                    <select
                      value={selectedSubscriptionId}
                      onChange={(e) => handleSelectSubscription(e.target.value)}
                      className="w-full px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">请选择要切换的订阅</option>
                      {savedSubscriptions.map((sub) => (
                        <option key={sub.id} value={sub.id}>
                          {sub.name || sub.url}
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-2">
                      选择订阅后会自动填充信息，点击“更新订阅”即可更换。
                    </p>
                  </div>
                )}

                {/* Subscription Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    订阅名称（可选）
                  </label>
                  <input
                    type="text"
                    value={subscriptionName}
                    onChange={(e) => setSubscriptionName(e.target.value)}
                    placeholder="例如：我的订阅"
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Subscription URL */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    订阅链接 *
                  </label>
                  <input
                    type="text"
                    value={subscriptionUrl}
                    onChange={(e) => setSubscriptionUrl(e.target.value)}
                    placeholder="https://example.com/subscription"
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Subscription Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    订阅类型
                  </label>
                  <div className="flex gap-4">
                    <label className="flex items-center">
                      <input
                        type="radio"
                        value="clash"
                        checked={subscriptionType === 'clash'}
                        onChange={(e) => setSubscriptionType(e.target.value as 'clash' | 'base64')}
                        className="mr-2"
                      />
                      <span className="text-gray-900 dark:text-white">Clash 订阅</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        value="base64"
                        checked={subscriptionType === 'base64'}
                        onChange={(e) => setSubscriptionType(e.target.value as 'clash' | 'base64')}
                        className="mr-2"
                      />
                      <span className="text-gray-900 dark:text-white">Base64 订阅</span>
                    </label>
                  </div>
                </div>

                {/* Info */}
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    <strong>提示：</strong> 输入订阅链接后点击"更新订阅"，系统会自动解析节点并保存到本地。
                  </p>
                </div>

                {/* Buttons */}
                <div className="flex gap-3 justify-end">
                  <Button
                    onClick={handleImportSubscription}
                    disabled={!subscriptionUrl.trim()}
                    className="bg-indigo-500 hover:bg-indigo-600"
                  >
                    <Plus size={18} />
                    导入订阅
                  </Button>
                  <Button
                    onClick={() => setShowSubscriptionModal(false)}
                    className="bg-gray-500 hover:bg-gray-600"
                  >
                    取消
                  </Button>
                  <Button
                    onClick={handleUpdateSubscription}
                    disabled={updating || !subscriptionUrl.trim()}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {updating ? '更新中...' : '更新订阅'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProxyPage;
