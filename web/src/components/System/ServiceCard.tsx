import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Button } from '../Common/Button';
import { GlassCard } from '../Common/GlassCard';

interface ServiceCardProps {
  name: string;
  displayName: string;
  description: string;
  status: 'running' | 'stopped' | 'loading' | 'error';
  onStart: () => Promise<void>;
  onStop: () => Promise<void>;
  onRestart: () => Promise<void>;
}

const ServiceCard: React.FC<ServiceCardProps> = ({
  name,
  displayName,
  description,
  status,
  onStart,
  onStop,
  onRestart,
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleAction = async (action: () => Promise<void>) => {
    setIsLoading(true);
    try {
      await action();
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return 'text-green-400';
      case 'stopped':
        return 'text-red-400';
      case 'loading':
        return 'text-yellow-400';
      case 'error':
        return 'text-orange-400';
      default:
        return 'text-gray-400';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'running':
        return '运行中';
      case 'stopped':
        return '已停止';
      case 'loading':
        return '加载中...';
      case 'error':
        return '错误';
      default:
        return '未知';
    }
  };

  return (
    <GlassCard className="p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-white mb-1">
            {displayName}
          </h3>
          <p className="text-sm text-gray-400 mb-2">{description}</p>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">状态:</span>
            <span className={`text-sm font-medium ${getStatusColor()}`}>
              {getStatusText()}
            </span>
          </div>
        </div>
      </div>

      <div className="flex gap-2">
        <Button
          onClick={() => handleAction(onStart)}
          disabled={status === 'running' || isLoading}
          variant="primary"
          size="sm"
        >
          启动
        </Button>
        <Button
          onClick={() => handleAction(onStop)}
          disabled={status === 'stopped' || isLoading}
          variant="danger"
          size="sm"
        >
          停止
        </Button>
        <Button
          onClick={() => handleAction(onRestart)}
          disabled={status === 'stopped' || isLoading}
          variant="secondary"
          size="sm"
        >
          重启
        </Button>
      </div>
    </GlassCard>
  );
};

export default ServiceCard;
