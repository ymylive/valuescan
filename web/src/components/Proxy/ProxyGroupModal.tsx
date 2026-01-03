import React, { useState, useEffect } from 'react';
import { Modal } from '../Common/Modal';
import { Button } from '../Common/Button';
import { Input } from '../Common/Input';
import { ProxyGroup, ProxyNode, ProxyGroupType } from '../../types/clash';

interface ProxyGroupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (group: ProxyGroup) => void;
  group?: ProxyGroup;
  nodes: ProxyNode[];
}

const ProxyGroupModal: React.FC<ProxyGroupModalProps> = ({
  isOpen,
  onClose,
  onSave,
  group,
  nodes
}) => {
  const [name, setName] = useState('');
  const [type, setType] = useState<ProxyGroupType>('select');
  const [selectedNodes, setSelectedNodes] = useState<string[]>([]);
  const [testUrl, setTestUrl] = useState('http://www.gstatic.com/generate_204');
  const [interval, setInterval] = useState(300);
  const [tolerance, setTolerance] = useState(150);

  useEffect(() => {
    if (group) {
      setName(group.name);
      setType(group.type);
      setSelectedNodes(group.proxies);
      setTestUrl(group.url || 'http://www.gstatic.com/generate_204');
      setInterval(group.interval || 300);
      setTolerance(group.tolerance || 150);
    } else {
      setName('');
      setType('select');
      setSelectedNodes([]);
      setTestUrl('http://www.gstatic.com/generate_204');
      setInterval(300);
      setTolerance(150);
    }
  }, [group, isOpen]);

  const handleSave = () => {
    const newGroup: ProxyGroup = {
      id: group?.id || Date.now().toString(),
      name,
      type,
      proxies: selectedNodes,
      url: ['url-test', 'fallback'].includes(type) ? testUrl : undefined,
      interval: ['url-test', 'fallback'].includes(type) ? interval : undefined,
      tolerance: type === 'url-test' ? tolerance : undefined,
    };
    onSave(newGroup);
    onClose();
  };

  const toggleNode = (nodeId: string) => {
    setSelectedNodes(prev =>
      prev.includes(nodeId)
        ? prev.filter(id => id !== nodeId)
        : [...prev, nodeId]
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={group ? '编辑策略组' : '添加策略组'}>
      <div className="space-y-4">
        {/* 策略组名称 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            策略组名称
          </label>
          <Input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="例如: 自动选择"
            className="w-full"
          />
        </div>

        {/* 策略组类型 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            策略组类型
          </label>
          <select
            value={type}
            onChange={e => setType(e.target.value as ProxyGroupType)}
            className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg"
          >
            <option value="select">手动选择 - 手动切换节点</option>
            <option value="url-test">自动测速 - 选择延迟最低的节点</option>
            <option value="fallback">故障转移 - 按顺序选择可用节点</option>
            <option value="load-balance">负载均衡 - 分散请求到多个节点</option>
          </select>
        </div>

        {/* 测试URL (url-test, fallback) */}
        {['url-test', 'fallback'].includes(type) && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              测试URL
            </label>
            <Input
              type="text"
              value={testUrl}
              onChange={e => setTestUrl(e.target.value)}
              className="w-full"
            />
          </div>
        )}

        {/* 测试间隔 (url-test, fallback) */}
        {['url-test', 'fallback'].includes(type) && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              测试间隔 (秒)
            </label>
            <Input
              type="number"
              value={interval}
              onChange={e => setInterval(Number(e.target.value))}
              className="w-full"
            />
          </div>
        )}

        {/* 容差 (url-test) */}
        {type === 'url-test' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              容差 (毫秒)
            </label>
            <Input
              type="number"
              value={tolerance}
              onChange={e => setTolerance(Number(e.target.value))}
              className="w-full"
            />
          </div>
        )}

        {/* 选择节点 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            选择节点 ({selectedNodes.length} 个已选)
          </label>
          <div className="max-h-60 overflow-y-auto border border-gray-300 dark:border-gray-600 rounded-lg p-2">
            {nodes.map(node => (
              <label
                key={node.id}
                className="flex items-center p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedNodes.includes(node.id)}
                  onChange={() => toggleNode(node.id)}
                  className="mr-2"
                />
                <span className="text-sm text-gray-900 dark:text-white">{node.name}</span>
              </label>
            ))}
          </div>
        </div>

        {/* 按钮 */}
        <div className="flex gap-3 pt-4">
          <Button
            onClick={onClose}
            className="flex-1 bg-gray-500 hover:bg-gray-600"
          >
            取消
          </Button>
          <Button
            onClick={handleSave}
            disabled={!name || selectedNodes.length === 0}
            className="flex-1 bg-green-500 hover:bg-green-600"
          >
            保存
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default ProxyGroupModal;
