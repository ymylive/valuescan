import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import ServiceCard from '../components/System/ServiceCard';
import { toast } from 'react-hot-toast';

interface Service {
  name: string;
  displayName: string;
  description: string;
  status: 'running' | 'stopped' | 'loading' | 'error';
}

const ServicesPage: React.FC = () => {
  const [services, setServices] = useState<Service[]>([
    {
      name: 'valuescan-monitor',
      displayName: 'Signal Monitor',
      description: 'ValueScan 信号监控服务 - 监控交易信号并发送 Telegram 通知',
      status: 'loading',
    },
    {
      name: 'valuescan-trader',
      displayName: 'Trading Bot',
      description: 'AI 交易机器人 - 自动执行交易策略',
      status: 'loading',
    },
    {
      name: 'valuescan-api',
      displayName: 'API Server',
      description: 'API 服务器 - 提供 Web 界面后端服务',
      status: 'loading',
    },
    {
      name: 'valuescan-token-refresher',
      displayName: 'Token Refresher',
      description: 'Token 刷新服务 - 自动刷新 ValueScan 登录凭证',
      status: 'loading',
    },
  ]);

  // 获取所有服务状态
  const fetchServicesStatus = async () => {
    try {
      const response = await fetch('/api/services/status');
      if (response.ok) {
        const data = await response.json();
        setServices((prev) =>
          prev.map((service) => ({
            ...service,
            status: data[service.name] || 'stopped',
          }))
        );
      }
    } catch (error) {
      console.error('Failed to fetch services status:', error);
      toast.error('获取服务状态失败');
    }
  };

  useEffect(() => {
    fetchServicesStatus();
    const interval = setInterval(fetchServicesStatus, 10000); // 每10秒刷新
    return () => clearInterval(interval);
  }, []);

  // 服务控制函数
  const handleServiceAction = async (
    serviceName: string,
    action: 'start' | 'stop' | 'restart'
  ) => {
    try {
      const response = await fetch(`/api/services/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service: serviceName }),
      });

      if (response.ok) {
        toast.success(`服务 ${action === 'start' ? '启动' : action === 'stop' ? '停止' : '重启'} 成功`);
        setTimeout(fetchServicesStatus, 2000); // 2秒后刷新状态
      } else {
        const error = await response.json();
        toast.error(error.message || '操作失败');
      }
    } catch (error) {
      console.error(`Failed to ${action} service:`, error);
      toast.error('操作失败，请检查网络连接');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-7xl mx-auto"
      >
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">服务管理</h1>
          <p className="text-gray-400">管理和监控系统服务状态</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {services.map((service) => (
            <ServiceCard
              key={service.name}
              name={service.name}
              displayName={service.displayName}
              description={service.description}
              status={service.status}
              onStart={() => handleServiceAction(service.name, 'start')}
              onStop={() => handleServiceAction(service.name, 'stop')}
              onRestart={() => handleServiceAction(service.name, 'restart')}
            />
          ))}
        </div>
      </motion.div>
    </div>
  );
};

export default ServicesPage;
