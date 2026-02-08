import React, { useEffect, useState } from 'react';
import { tradingApi } from '../../services/tradingApi';
import { TraderConfig } from '../../types/trading';

interface TraderSelectorProps {
  selectedTraderId: string;
  onSelect: (traderId: string) => void;
  className?: string;
}

export const TraderSelector: React.FC<TraderSelectorProps> = ({
  selectedTraderId,
  onSelect,
  className = '',
}) => {
  const [traders, setTraders] = useState<TraderConfig[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTraders = async () => {
      try {
        const data = await tradingApi.getTraders();
        // @ts-ignore
        setTraders(data || []);
      } catch (error) {
        console.error('Failed to fetch traders:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTraders();
  }, []);

  if (loading) {
    return (
      <div className={`animate-pulse ${className}`}>
        <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      </div>
    );
  }

  return (
    <select
      value={selectedTraderId}
      onChange={(e) => onSelect(e.target.value)}
      className={`w-full px-4 py-2 rounded-lg border bg-white/50 dark:bg-black/20
        border-gray-200 dark:border-white/10 text-gray-900 dark:text-white
        outline-none focus:ring-2 focus:ring-green-500 transition-all ${className}`}
    >
      <option value="">Select Trader</option>
      {traders.map((trader) => (
        <option key={trader.trader_id} value={trader.trader_id}>
          {trader.trader_name} {trader.is_running ? '(Running)' : '(Stopped)'}
        </option>
      ))}
    </select>
  );
};
