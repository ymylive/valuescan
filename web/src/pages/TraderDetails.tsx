import React, { useState, useEffect } from 'react';
import { User, Play, Pause, TrendingUp } from 'lucide-react';
import { GlassCard } from '../components/Common/GlassCard';
import { Button } from '../components/Common/Button';
import { TraderConfig, AccountInfo, Position } from '../types/trading';
import { tradingApi } from '../services/tradingApi';
import { logger } from '../services/loggerService';

interface TraderDetailsProps {
  traderId: string;
}

const TraderDetails: React.FC<TraderDetailsProps> = ({ traderId }) => {
  const [trader, setTrader] = useState<TraderConfig | null>(null);
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'positions' | 'history' | 'performance'>('positions');

  useEffect(() => {
    loadTraderData();
  }, [traderId]);

  const loadTraderData = async () => {
    setLoading(true);
    setError(null);
    logger.info('TraderDetails', '开始加载交易者数据', {
      traderId,
      timestamp: new Date().toISOString()
    });
    try {
      const [traderResponse, accountResponse, positionsResponse] = await Promise.all([
        tradingApi.getTrader(traderId),
        tradingApi.getAccount(traderId),
        tradingApi.getPositions(traderId),
      ]);
      setTrader(traderResponse.data);
      setAccount(accountResponse.data);
      setPositions(positionsResponse.data);
      logger.info('TraderDetails', '交易者数据加载成功', {
        traderId,
        traderName: traderResponse.data.trader_name,
        totalPnl: accountResponse.data.total_pnl,
        positionsCount: positionsResponse.data.length,
        positions: positionsResponse.data.map(p => ({
          symbol: p.symbol,
          side: p.side,
          size: p.size,
          unrealizedPnl: p.unrealized_pnl
        }))
      });
    } catch (err) {
      setError('加载交易者数据失败');
      logger.error('TraderDetails', '加载交易者数据失败', err as Error, {
        traderId,
        errorDetails: err
      });
      console.error('Failed to load trader data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleTrader = async () => {
    if (!trader) return;
    try {
      if (trader.is_running) {
        await tradingApi.stopTrader(traderId);
      } else {
        await tradingApi.startTrader(traderId);
      }
      await loadTraderData();
    } catch (err) {
      console.error('Failed to toggle trader:', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <User className="text-blue-500" size={32} />
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {trader?.trader_name || '加载中...'}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {trader?.trader_id}
            </p>
          </div>
        </div>

        {trader && (
          <Button
            onClick={handleToggleTrader}
            className={`flex items-center gap-2 ${
              trader.is_running
                ? 'bg-red-500 hover:bg-red-600'
                : 'bg-green-500 hover:bg-green-600'
            }`}
          >
            {trader.is_running ? (
              <>
                <Pause size={18} />
                停止交易
              </>
            ) : (
              <>
                <Play size={18} />
                启动交易
              </>
            )}
          </Button>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 rounded-lg">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      )}

      {/* Account Overview */}
      {!loading && !error && account && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <GlassCard className="p-6">
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">总权益</h3>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              ${account.total_equity.toFixed(2)}
            </p>
          </GlassCard>

          <GlassCard className="p-6">
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">可用余额</h3>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              ${account.available_balance.toFixed(2)}
            </p>
          </GlassCard>

          <GlassCard className="p-6">
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">总盈亏</h3>
            <p className={`text-2xl font-bold ${
              account.total_pnl >= 0
                ? 'text-green-600 dark:text-green-400'
                : 'text-red-600 dark:text-red-400'
            }`}>
              ${account.total_pnl.toFixed(2)} ({account.total_pnl_pct.toFixed(2)}%)
            </p>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

export default TraderDetails;
