import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { PageContainer } from '../../components/layout';
import { Button, Badge } from '../../components/ui';
import { GlassCard } from '../../components/shared';
import { Play, Square, RotateCcw } from 'lucide-react';
import { useToastStore } from '../../stores';
import api, { toApiError } from '../../services/api';

interface Service {
  name: string;
  displayName: string;
  description: string;
  status: 'running' | 'stopped' | 'loading' | 'error';
}

export const ServicesPage = () => {
  const addToast = useToastStore((state) => state.addToast);
  const [services, setServices] = useState<Service[]>([
    { name: 'signal-monitor', displayName: 'Signal Monitor', description: 'Signal monitor service', status: 'loading' },
    { name: 'signal-api', displayName: 'API Server', description: 'API service', status: 'loading' },
  ]);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await api.get('/services/status') as Record<string, Service['status']>;
      setServices((prev) => prev.map((s) => ({ ...s, status: data[s.name] || 'stopped' })));
    } catch (error) {
      addToast('error', toApiError(error).message || 'Failed to load service status');
    }
  }, [addToast]);

  useEffect(() => {
    void fetchStatus();
    const interval = setInterval(() => {
      void fetchStatus();
    }, 10000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleAction = async (name: string, action: 'start' | 'stop' | 'restart') => {
    try {
      const res = await api.post(`/services/${action}`, { service: name }) as { success?: boolean; message?: string };
      if (res?.success) {
        addToast('success', `Service ${action} succeeded`);
        setTimeout(() => {
          void fetchStatus();
        }, 2000);
      } else {
        addToast('error', res?.message || 'Action failed');
      }
    } catch (error) {
      addToast('error', toApiError(error).message || 'Action failed');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running':
        return <Badge variant="success">Running</Badge>;
      case 'stopped':
        return <Badge variant="error">Stopped</Badge>;
      case 'loading':
        return <Badge variant="info">Loading</Badge>;
      default:
        return <Badge variant="warning">Error</Badge>;
    }
  };

  return (
    <PageContainer>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Service Management</h2>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Manage and monitor system services</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {services.map((service, index) => (
            <motion.div
              key={service.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <GlassCard className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{service.displayName}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{service.description}</p>
                  </div>
                  {getStatusBadge(service.status)}
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => handleAction(service.name, 'start')} disabled={service.status === 'running'}>
                    <Play className="w-4 h-4 mr-1" /> Start
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => handleAction(service.name, 'stop')} disabled={service.status === 'stopped'}>
                    <Square className="w-4 h-4 mr-1" /> Stop
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => handleAction(service.name, 'restart')}>
                    <RotateCcw className="w-4 h-4 mr-1" /> Restart
                  </Button>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      </div>
    </PageContainer>
  );
};

export default ServicesPage;
