import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '../components/Common/GlassCard';
import { Button } from '../components/Common/Button';
import api from '../services/api';
import { Zap, Plus, Copy, Trash2 } from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';

interface StrategyConfig {
  id: string;
  name: string;
  description: string;
  timeframe: string;
}

const Strategies: React.FC = () => {
  const { t } = useTranslation();
  const [strategies, setStrategies] = useState<StrategyConfig[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStrategies();
  }, []);

  const fetchStrategies = async () => {
    try {
      const data = await api.get<StrategyConfig[]>('/strategies');
      // @ts-ignore
      setStrategies(data || []);
    } catch (error) {
      toast.error(t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete strategy?')) return;
    try {
      await api.delete(`/strategies/${id}`);
      toast.success('Strategy deleted');
      fetchStrategies();
    } catch (error) {
      toast.error('Delete failed');
    }
  };

  const handleDuplicate = async (id: string) => {
    try {
      await api.post(`/strategies/${id}/duplicate`);
      toast.success('Strategy duplicated');
      fetchStrategies();
    } catch (error) {
      toast.error('Duplicate failed');
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">{t('common.loading')}</div>;

  return (
    <div className="space-y-6">
      <Toaster position="top-right" />

      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Zap className="text-green-500" />
          {t('common.strategies')}
        </h2>
        <Button>
          <Plus size={20} />
          Create Strategy
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {strategies.map((strategy) => (
          <GlassCard key={strategy.id} animate className="p-6 relative">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400">
                <Zap size={24} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white">{strategy.name}</h3>
                <span className="text-sm text-gray-500">{strategy.timeframe}</span>
              </div>
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-300 mb-6 h-10 overflow-hidden text-ellipsis">
              {strategy.description || 'No description'}
            </p>

            <div className="flex gap-2 justify-end pt-4 border-t border-gray-100 dark:border-white/5">
              <Button size="sm" variant="secondary" onClick={() => handleDuplicate(strategy.id)}>
                <Copy size={16} />
              </Button>
              <Button size="sm" variant="danger" onClick={() => handleDelete(strategy.id)}>
                <Trash2 size={16} />
              </Button>
            </div>
          </GlassCard>
        ))}
      </div>
    </div>
  );
};

export default Strategies;