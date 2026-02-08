import { useState } from 'react';
import { Wifi, Copy, CheckCircle, AlertCircle, RefreshCw, ExternalLink, Link as LinkIcon } from 'lucide-react';
import { PageContainer } from '../../components/layout';
import { Button, Input, Modal } from '../../components/ui';
import { GlassCard } from '../../components/shared';
import { useProxyData } from './hooks/useProxyData';
import { useToast } from '../../hooks';

export const ProxyPage = () => {
  const toast = useToast();
  const { serviceStatus, checking, loading, checkStatus, startService, updateSubscription } = useProxyData();
  const [copied, setCopied] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [subUrl, setSubUrl] = useState('');
  const [subType, setSubType] = useState<'clash' | 'base64'>('clash');
  const [updating, setUpdating] = useState(false);

  const clashApiUrl = `${window.location.protocol}//${window.location.host}/clash-api`;

  const handleCopy = () => {
    navigator.clipboard.writeText(clashApiUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleUpdate = async () => {
    if (!subUrl.trim()) return toast.error('请输入订阅链接');
    setUpdating(true);
    const result = await updateSubscription(subUrl, subType);
    setUpdating(false);
    if (result.success) {
      toast.success(`订阅更新成功！解析到 ${result.count} 个节点`);
      setShowModal(false);
      setSubUrl('');
    } else {
      toast.error(result.error || '订阅更新失败');
    }
  };

  return (
    <PageContainer>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Wifi className="text-green-500" size={32} />
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">代理节点管理</h2>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => setShowModal(true)}><LinkIcon className="w-4 h-4 mr-2" />订阅管理</Button>
            <Button variant="secondary" onClick={checkStatus} disabled={checking}>
              <RefreshCw className={`w-4 h-4 mr-2 ${checking ? 'animate-spin' : ''}`} />刷新状态
            </Button>
          </div>
        </div>

        {serviceStatus && !serviceStatus.running && (
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="text-yellow-600 dark:text-yellow-400 flex-shrink-0" size={20} />
              <div className="flex-1">
                <h3 className="font-semibold text-yellow-800 dark:text-yellow-200">Clash 服务未运行</h3>
                <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-3">请先启动 Clash 服务</p>
                <Button onClick={startService} disabled={loading}>{loading ? '启动中...' : '启动服务'}</Button>
              </div>
            </div>
          </div>
        )}

        {serviceStatus?.running && (
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
              <div>
                <h3 className="font-semibold text-green-800 dark:text-green-200">Clash 服务运行中</h3>
                <p className="text-sm text-green-700 dark:text-green-300">端口 {serviceStatus.port}</p>
              </div>
            </div>
          </div>
        )}

        <GlassCard className="p-8">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <Wifi className="text-green-500" size={48} />
              <div>
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">使用 MetaCubeX 管理 Clash 代理</h3>
                <p className="text-gray-600 dark:text-gray-400 mt-1">MetaCubeX 是 Mihomo 的官方 Web 管理界面</p>
              </div>
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 pt-6 space-y-4">
              <div className="flex gap-4 items-start">
                <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold">1</div>
                <div className="flex-1">
                  <p className="font-medium text-gray-900 dark:text-white mb-2">复制 Clash API 地址</p>
                  <div className="flex gap-2">
                    <Input value={clashApiUrl} readOnly className="flex-1" />
                    <Button onClick={handleCopy}>{copied ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}</Button>
                  </div>
                </div>
              </div>

              <div className="flex gap-4 items-start">
                <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold">2</div>
                <div className="flex-1">
                  <p className="font-medium text-gray-900 dark:text-white mb-2">打开 MetaCubeX 管理界面</p>
                  <Button onClick={() => window.open('https://metacubex.github.io/metacubexd/', '_blank')}>
                    <ExternalLink className="w-4 h-4 mr-2" />打开 MetaCubeX
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </GlassCard>

        <Modal isOpen={showModal} onClose={() => setShowModal(false)} title="订阅管理">
          <div className="space-y-4">
            <Input label="订阅链接" value={subUrl} onChange={(e) => setSubUrl(e.target.value)} placeholder="https://..." />
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">订阅类型</label>
              <div className="flex gap-4">
                {(['clash', 'base64'] as const).map((t) => (
                  <label key={t} className="flex items-center">
                    <input type="radio" value={t} checked={subType === t} onChange={() => setSubType(t)} className="mr-2" />
                    <span className="text-gray-900 dark:text-white">{t === 'clash' ? 'Clash 订阅' : 'Base64 订阅'}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex gap-3 justify-end">
              <Button variant="secondary" onClick={() => setShowModal(false)}>取消</Button>
              <Button onClick={handleUpdate} disabled={updating || !subUrl.trim()}>{updating ? '更新中...' : '更新订阅'}</Button>
            </div>
          </div>
        </Modal>
      </div>
    </PageContainer>
  );
};

export default ProxyPage;
