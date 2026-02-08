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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">服务管理</h2>
          <p className="text-gray-600 dark:text-gray-400 mt-1">管理和监控系统服务状态</p>
        </div>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {services.map((service, index) => (
          <motion.div
            key={service.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <ServiceCard
              name={service.name}
              displayName={service.displayName}
              description={service.description}
              status={service.status}
              onStart={() => handleServiceAction(service.name, 'start')}
              onStop={() => handleServiceAction(service.name, 'stop')}
              onRestart={() => handleServiceAction(service.name, 'restart')}
            />
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default ServicesPage;
