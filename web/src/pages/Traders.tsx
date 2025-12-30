import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '../components/Common/GlassCard';
import { Button } from '../components/Common/Button';
import { Input } from '../components/Common/Input';
import { Modal } from '../components/Common/Modal';
import api from '../services/api';
import { Users, Plus, Play, Square, Trash2, TrendingUp, Settings2 } from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';

interface TraderConfig {
  trader_id: string;
  trader_name: string;
  ai_model: string;
  exchange_id: string;
  is_running: boolean;
  initial_balance: number;
  strategy_id: string;
  strategy_name?: string;
}

const Traders: React.FC = () => {
  const { t } = useTranslation();
  const [traders, setTraders] = useState<TraderConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Dependencies for dropdowns
  const [models, setModels] = useState<any[]>([]);
  const [exchanges, setExchanges] = useState<any[]>([]);
  const [strategies, setStrategies] = useState<any[]>([]);

  // Form State
  const [formData, setFormData] = useState({
    name: '',
    ai_model_id: '',
    exchange_id: '',
    strategy_id: '',
    initial_balance: 1000,
    btc_eth_leverage: 10,
    altcoin_leverage: 5,
    trading_symbols: 'BTCUSDT,ETHUSDT',
    is_cross_margin: true
  });

  useEffect(() => {
    fetchTraders();
    fetchDependencies();
  }, []);

  const fetchDependencies = async () => {
    try {
      const [m, e, s] = await Promise.all([
        api.get('/models'),
        api.get('/exchanges'),
        api.get('/strategies')
      ]);
      // @ts-ignore
      setModels(m || []);
      // @ts-ignore
      setExchanges(e || []);
      // @ts-ignore
      setStrategies(s || []);
    } catch (error) {
      console.error(error);
    }
  };

  const fetchTraders = async () => {
    try {
      const data = await api.get<TraderConfig[]>('/my-traders');
      // @ts-ignore
      setTraders(data || []);
    } catch (error) {
      toast.error(t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleStartStop = async (id: string, isRunning: boolean) => {
    try {
      if (isRunning) {
        await api.post(`/traders/${id}/stop`);
      } else {
        await api.post(`/traders/${id}/start`);
      }
      toast.success(isRunning ? 'Trader stopped' : 'Trader started');
      fetchTraders();
    } catch (error) {
      toast.error('Operation failed');
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete trader?')) return;
    try {
      await api.delete(`/traders/${id}`);
      toast.success('Trader deleted');
      fetchTraders();
    } catch (error) {
      toast.error('Delete failed');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/traders', formData);
      toast.success('Trader created');
      setIsModalOpen(false);
      fetchTraders();
    } catch (error: any) {
        const errorMsg = error.response?.data?.error || 'Create failed';
        toast.error(errorMsg);
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">{t('common.loading')}</div>;

  return (
    <div className="space-y-6">
      <Toaster position="top-right" />

      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Users className="text-green-500" />
          {t('common.traders')}
        </h2>
        <Button onClick={() => setIsModalOpen(true)}>
          <Plus size={20} />
          {t('traders.newTrader')}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {traders.map((trader) => (
          <GlassCard key={trader.trader_id} animate className="p-6 relative">
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${
                  trader.is_running 
                    ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400' 
                    : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                }`}>
                  <TrendingUp size={24} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white">{trader.trader_name}</h3>
                  <div className="text-xs text-gray-500 flex items-center gap-1">
                    <span className={`w-2 h-2 rounded-full ${trader.is_running ? 'bg-green-500' : 'bg-gray-400'}`} />
                    {trader.is_running ? 'Running' : 'Stopped'}
                  </div>
                </div>
              </div>
              <div className="flex gap-1">
                <button onClick={() => handleDelete(trader.trader_id)} className="p-2 text-gray-400 hover:text-red-500 transition-colors">
                  <Trash2 size={18} />
                </button>
              </div>
            </div>

            <div className="space-y-3 mb-6">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500 dark:text-gray-400">Balance</span>
                <span className="font-mono font-medium dark:text-white">${trader.initial_balance.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500 dark:text-gray-400">Model</span>
                <span className="dark:text-white">{trader.ai_model}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500 dark:text-gray-400">Strategy</span>
                <span className="dark:text-white">{trader.strategy_name || 'N/A'}</span>
              </div>
            </div>

            <div className="flex gap-3">
              <Button 
                className="flex-1" 
                variant={trader.is_running ? 'danger' : 'primary'}
                onClick={() => handleStartStop(trader.trader_id, trader.is_running)}
              >
                {trader.is_running ? (
                  <><Square size={16} fill="currentColor" /> Stop</>
                ) : (
                  <><Play size={16} fill="currentColor" /> Start</>
                )}
              </Button>
              <Button variant="secondary">
                <Settings2 size={16} />
              </Button>
            </div>
          </GlassCard>
        ))}
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create AI Trader"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input 
            label="Name" 
            value={formData.name}
            onChange={e => setFormData({...formData, name: e.target.value})}
            required
            placeholder="e.g. BTC Alpha Trader"
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">AI Model</label>
            <select
              className="w-full px-4 py-2 rounded-lg border bg-white/50 dark:bg-black/20 border-gray-200 dark:border-white/10 text-gray-900 dark:text-white outline-none"
              value={formData.ai_model_id}
              onChange={e => setFormData({...formData, ai_model_id: e.target.value})}
              required
            >
              <option value="">Select AI Model</option>
              {models.filter((m: any) => m.enabled).map((m: any) => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Exchange Account</label>
            <select
              className="w-full px-4 py-2 rounded-lg border bg-white/50 dark:bg-black/20 border-gray-200 dark:border-white/10 text-gray-900 dark:text-white outline-none"
              value={formData.exchange_id}
              onChange={e => setFormData({...formData, exchange_id: e.target.value})}
              required
            >
              <option value="">Select Exchange</option>
              {exchanges.map((e: any) => (
                <option key={e.id} value={e.id}>{e.account_name} ({e.exchange_type})</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Strategy</label>
            <select
              className="w-full px-4 py-2 rounded-lg border bg-white/50 dark:bg-black/20 border-gray-200 dark:border-white/10 text-gray-900 dark:text-white outline-none"
              value={formData.strategy_id}
              onChange={e => setFormData({...formData, strategy_id: e.target.value})}
              required
            >
              <option value="">Select Strategy</option>
              {strategies.map((s: any) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input 
              label="BTC/ETH Lev." 
              type="number"
              value={formData.btc_eth_leverage}
              onChange={e => setFormData({...formData, btc_eth_leverage: parseInt(e.target.value)})}
            />
             <Input 
              label="Altcoin Lev." 
              type="number"
              value={formData.altcoin_leverage}
              onChange={e => setFormData({...formData, altcoin_leverage: parseInt(e.target.value)})}
            />
          </div>

          <Input 
            label="Initial Balance (USDT)" 
            type="number"
            value={formData.initial_balance}
            onChange={e => setFormData({...formData, initial_balance: parseFloat(e.target.value)})}
          />

          <div className="flex justify-end gap-3 mt-6">
            <Button type="button" variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">
              Create Trader
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default Traders;