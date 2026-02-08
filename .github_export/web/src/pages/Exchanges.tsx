import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '../components/Common/GlassCard';
import { Button } from '../components/Common/Button';
import { Input } from '../components/Common/Input';
import { Modal } from '../components/Common/Modal';
import api from '../services/api';
import { Wallet, Plus, Trash2 } from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';

interface ExchangeConfig {
  id: string;
  name: string; // Display name
  account_name: string;
  exchange_type: string;
  enabled: boolean;
  testnet: boolean;
  // Specific fields
  hyperliquidWalletAddr?: string;
  asterUser?: string;
  lighterWalletAddr?: string;
}

const Exchanges: React.FC = () => {
  const { t } = useTranslation();
  const [exchanges, setExchanges] = useState<ExchangeConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Form State
  const [formData, setFormData] = useState({
    exchange_type: 'binance',
    account_name: '',
    api_key: '',
    secret_key: '',
    passphrase: '',
    testnet: false,
    enabled: true,
    // Hyperliquid
    hyperliquid_wallet_addr: '',
    // Aster
    aster_user: '',
    aster_signer: '',
    aster_private_key: '',
    // Lighter
    lighter_wallet_addr: '',
    lighter_private_key: '',
    lighter_api_key_private_key: '',
    lighter_api_key_index: 0
  });

  useEffect(() => {
    fetchExchanges();
  }, []);

  const fetchExchanges = async () => {
    try {
      const data = await api.get<ExchangeConfig[]>('/exchanges');
      // @ts-ignore
      setExchanges(data || []);
    } catch (error) {
      console.error('Failed to fetch exchanges', error);
      toast.error(t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(t('Are you sure you want to delete this exchange?'))) return;
    try {
      await api.delete(`/exchanges/${id}`);
      toast.success(t('common.success'));
      fetchExchanges();
    } catch (error) {
      toast.error(t('common.error'));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/exchanges', formData);
      toast.success(t('common.success'));
      setIsModalOpen(false);
      fetchExchanges();
      // Reset form
      setFormData({
        exchange_type: 'binance',
        account_name: '',
        api_key: '',
        secret_key: '',
        passphrase: '',
        testnet: false,
        enabled: true,
        hyperliquid_wallet_addr: '',
        aster_user: '',
        aster_signer: '',
        aster_private_key: '',
        lighter_wallet_addr: '',
        lighter_private_key: '',
        lighter_api_key_private_key: '',
        lighter_api_key_index: 0
      });
    } catch (error) {
      console.error(error);
      toast.error(t('common.error'));
    }
  };

  const renderFormFields = () => {
    switch (formData.exchange_type) {
      case 'binance':
      case 'bybit':
      case 'bitget':
        return (
          <>
            <Input 
              label="API Key" 
              value={formData.api_key}
              onChange={e => setFormData({...formData, api_key: e.target.value})}
              required
            />
            <Input 
              label="Secret Key" 
              type="password"
              value={formData.secret_key}
              onChange={e => setFormData({...formData, secret_key: e.target.value})}
              required
            />
          </>
        );
      case 'okx':
        return (
          <>
            <Input 
              label="API Key" 
              value={formData.api_key}
              onChange={e => setFormData({...formData, api_key: e.target.value})}
              required
            />
            <Input 
              label="Secret Key" 
              type="password"
              value={formData.secret_key}
              onChange={e => setFormData({...formData, secret_key: e.target.value})}
              required
            />
            <Input 
              label="Passphrase" 
              type="password"
              value={formData.passphrase}
              onChange={e => setFormData({...formData, passphrase: e.target.value})}
              required
            />
          </>
        );
      case 'hyperliquid':
        return (
          <>
            <Input 
              label="Wallet Address" 
              value={formData.hyperliquid_wallet_addr}
              onChange={e => setFormData({...formData, hyperliquid_wallet_addr: e.target.value})}
              required
            />
            <Input 
              label="Private Key (API Key)" 
              type="password"
              value={formData.api_key}
              onChange={e => setFormData({...formData, api_key: e.target.value})}
              required
            />
          </>
        );
      default:
        return null;
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">{t('common.loading')}</div>;

  return (
    <div className="space-y-6">
      <Toaster position="top-right" />

      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Wallet className="text-green-500" />
          {t('common.exchanges')}
        </h2>
        <Button onClick={() => setIsModalOpen(true)}>
          <Plus size={20} />
          Add Exchange
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {exchanges.map((ex) => (
          <GlassCard key={ex.id} animate className="p-6 relative group">
            <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
              <button 
                onClick={() => handleDelete(ex.id)}
                className="text-red-500 hover:text-red-700 p-2"
              >
                <Trash2 size={18} />
              </button>
            </div>
            
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 rounded-full bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400">
                <Wallet size={24} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white">{ex.account_name}</h3>
                <span className="text-sm text-gray-500 uppercase">{ex.exchange_type} {ex.testnet && '(Testnet)'}</span>
              </div>
            </div>

            <div className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
              <div className="flex justify-between">
                <span>Status:</span>
                <span className={ex.enabled ? 'text-green-500' : 'text-gray-500'}>
                  {ex.enabled ? 'Active' : 'Disabled'}
                </span>
              </div>
              {ex.hyperliquidWalletAddr && (
                <div className="flex justify-between">
                  <span>Wallet:</span>
                  <span className="font-mono text-xs">{ex.hyperliquidWalletAddr.slice(0, 6)}...{ex.hyperliquidWalletAddr.slice(-4)}</span>
                </div>
              )}
            </div>
          </GlassCard>
        ))}
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Connect Exchange"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Exchange</label>
            <select
              className="w-full px-4 py-2 rounded-lg border bg-white/50 dark:bg-black/20 border-gray-200 dark:border-white/10 text-gray-900 dark:text-white focus:ring-2 focus:ring-green-500/50 outline-none"
              value={formData.exchange_type}
              onChange={e => setFormData({...formData, exchange_type: e.target.value})}
            >
              <option value="binance">Binance Futures</option>
              <option value="okx">OKX</option>
              <option value="bybit">Bybit</option>
              <option value="bitget">Bitget</option>
              <option value="hyperliquid">Hyperliquid (DEX)</option>
            </select>
          </div>

          <Input 
            label="Account Name" 
            placeholder="e.g. Main Account"
            value={formData.account_name}
            onChange={e => setFormData({...formData, account_name: e.target.value})}
            required
          />

          {renderFormFields()}

          <div className="flex items-center gap-2 py-2">
            <input 
              type="checkbox" 
              id="testnet"
              checked={formData.testnet}
              onChange={e => setFormData({...formData, testnet: e.target.checked})}
              className="rounded text-green-500 focus:ring-green-500"
            />
            <label htmlFor="testnet" className="text-sm text-gray-700 dark:text-gray-300">
              Use Testnet
            </label>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <Button type="button" variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">
              Connect
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default Exchanges;