import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '../components/Common/GlassCard';
import api from '../services/api';
import { Settings as SettingsIcon, Server, Globe } from 'lucide-react';

interface SystemConfig {
  registration_enabled: boolean;
  btc_eth_leverage: number;
  altcoin_leverage: number;
}

interface NetworkInfo {
  public_ip: string;
  message: string;
}

const Settings: React.FC = () => {
  const { t } = useTranslation();
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [network, setNetwork] = useState<NetworkInfo | null>(null);
  
  useEffect(() => {
    fetchConfig();
    fetchNetwork();
  }, []);

  const fetchConfig = async () => {
    try {
      const data = await api.get<SystemConfig>('/config');
      // @ts-ignore
      setConfig(data);
    } catch (error) {
      console.error(error);
    }
  };

  const fetchNetwork = async () => {
    try {
      const data = await api.get<NetworkInfo>('/server-ip');
      // @ts-ignore
      setNetwork(data);
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-6">
        <SettingsIcon className="text-green-500" size={32} />
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{t('common.settings')}</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <GlassCard className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <Server className="text-blue-500" />
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">System Defaults</h3>
          </div>
          {config ? (
            <div className="space-y-3">
              <div className="flex justify-between p-3 bg-gray-50 dark:bg-white/5 rounded-lg">
                <span className="text-gray-600 dark:text-gray-300">Registration</span>
                <span className={config.registration_enabled ? 'text-green-500' : 'text-red-500'}>
                  {config.registration_enabled ? 'Open' : 'Closed'}
                </span>
              </div>
              <div className="flex justify-between p-3 bg-gray-50 dark:bg-white/5 rounded-lg">
                <span className="text-gray-600 dark:text-gray-300">Default BTC/ETH Lev.</span>
                <span className="font-mono">{config.btc_eth_leverage}x</span>
              </div>
              <div className="flex justify-between p-3 bg-gray-50 dark:bg-white/5 rounded-lg">
                <span className="text-gray-600 dark:text-gray-300">Default Altcoin Lev.</span>
                <span className="font-mono">{config.altcoin_leverage}x</span>
              </div>
            </div>
          ) : (
            <div className="animate-pulse space-y-3">
               <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
               <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
            </div>
          )}
        </GlassCard>

        <GlassCard className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <Globe className="text-purple-500" />
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">Network Info</h3>
          </div>
          {network ? (
            <div className="space-y-3">
              <div className="p-4 bg-gray-50 dark:bg-white/5 rounded-lg border border-gray-100 dark:border-white/10">
                <label className="text-xs text-gray-500 uppercase font-bold">Server Public IP</label>
                <div className="text-xl font-mono mt-1 text-gray-900 dark:text-white select-all">
                  {network.public_ip || 'Unavailable'}
                </div>
              </div>
              <p className="text-sm text-gray-500">{network.message}</p>
            </div>
          ) : (
             <div className="animate-pulse h-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
          )}
        </GlassCard>
      </div>
    </div>
  );
};

export default Settings;