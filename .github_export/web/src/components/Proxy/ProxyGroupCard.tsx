import React, { useState } from 'react';
import { Plus, Trash2, Edit2 } from 'lucide-react';
import { GlassCard } from '../Common/GlassCard';
import { Button } from '../Common/Button';
import { ProxyGroup, ProxyNode } from '../../types/clash';

interface ProxyGroupCardProps {
  group: ProxyGroup;
  nodes: ProxyNode[];
  onEdit: (group: ProxyGroup) => void;
  onDelete: (groupId: string) => void;
}

const ProxyGroupCard: React.FC<ProxyGroupCardProps> = ({ group, nodes, onEdit, onDelete }) => {
  const getGroupTypeLabel = (type: string) => {
    const labels = {
      'select': '手动选择',
      'url-test': '自动测速',
      'fallback': '故障转移',
      'load-balance': '负载均衡'
    };
    return labels[type as keyof typeof labels] || type;
  };

  const getGroupTypeColor = (type: string) => {
    const colors = {
      'select': 'text-blue-500',
      'url-test': 'text-green-500',
      'fallback': 'text-yellow-500',
      'load-balance': 'text-purple-500'
    };
    return colors[type as keyof typeof colors] || 'text-gray-500';
  };

  return (
    <GlassCard className="p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h4 className="font-medium text-gray-900 dark:text-white">{group.name}</h4>
          <p className={`text-sm ${getGroupTypeColor(group.type)}`}>
            {getGroupTypeLabel(group.type)}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => onEdit(group)}
            className="px-2 py-1 text-sm bg-blue-500 hover:bg-blue-600"
          >
            <Edit2 size={14} />
          </Button>
          <Button
            onClick={() => onDelete(group.id)}
            className="px-2 py-1 text-sm bg-red-500 hover:bg-red-600"
          >
            <Trash2 size={14} />
          </Button>
        </div>
      </div>

      <div className="text-sm text-gray-600 dark:text-gray-400">
        <div>节点数: {group.proxies.length}</div>
        {group.url && <div>测试URL: {group.url}</div>}
        {group.interval && <div>测试间隔: {group.interval}秒</div>}
      </div>
    </GlassCard>
  );
};

export default ProxyGroupCard;
