import React, { useState, useEffect } from 'react';
import { TrendingUp, Award, Target, AlertCircle } from 'lucide-react';
import { GlassCard } from '../components/Common/GlassCard';
import { Statistics } from '../types/trading';
import { tradingApi } from '../services/tradingApi';
import { logger } from '../services/loggerService';

const PerformanceStats: React.FC = () => {
  const [stats, setStats] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTrader, setSelectedTrader] = useState<string>('all');

  useEffect(() => {
    loadStatistics();
  }, [selectedTrader]);

  const loadStatistics = async () => {
    setLoading(true);
    setError(null);
    logger.info('PerformanceStats', '开始加载性能统计', {
      trader: selectedTrader,
      timestamp: new Date().toISOString()
    });
    try {
      const response = await tradingApi.getStatistics(selectedTrader === 'all' ? '' : selectedTrader);
      setStats(response.data);
      logger.info('PerformanceStats', '性能统计加载成功', {
        trader: selectedTrader,
        winRate: response.data.win_rate,
        totalPnl: response.data.total_pnl,
        profitFactor: response.data.profit_factor,
        maxDrawdown: response.data.max_drawdown,
        totalTrades: response.data.total_trades,
        winningTrades: response.data.winning_trades,
        losingTrades: response.data.losing_trades
      });
    } catch (err) {
      setError('加载性能统计失败');
      logger.error('PerformanceStats', '加载性能统计失败', err as Error, {
        trader: selectedTrader,
        errorDetails: err
      });
      console.error('Failed to load statistics:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TrendingUp className="text-green-500" size={32} />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">性能统计</h2>
        </div>

        {/* Trader Selector */}
        <div className="w-64">
          <select
            value={selectedTrader}
            onChange={(e) => setSelectedTrader(e.target.value)}
            className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg"
          >
            <option value="all">全部交易者</option>
          </select>
        </div>
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
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500"></div>
        </div>
      )}

      {/* Key Metrics */}
      {!loading && !error && stats && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Win Rate */}
            <GlassCard className="p-6">
              <div className="flex items-center justify-between mb-4">
                <Target className="text-blue-500" size={24} />
                <span className="text-2xl font-bold text-gray-900 dark:text-white">
                  {(stats.win_rate * 100).toFixed(1)}%
                </span>
              </div>
              <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">胜率</h3>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                {stats.winning_trades} 胜 / {stats.losing_trades} 负
              </p>
            </GlassCard>

            {/* Total PnL */}
            <GlassCard className="p-6">
              <div className="flex items-center justify-between mb-4">
                <TrendingUp className={stats.total_pnl >= 0 ? 'text-green-500' : 'text-red-500'} size={24} />
                <span className={`text-2xl font-bold ${stats.total_pnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                  ${stats.total_pnl.toFixed(2)}
                </span>
              </div>
              <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">总盈亏</h3>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                {stats.total_pnl_pct.toFixed(2)}% 收益率
              </p>
            </GlassCard>

            {/* Profit Factor */}
            <GlassCard className="p-6">
              <div className="flex items-center justify-between mb-4">
                <Award className="text-purple-500" size={24} />
                <span className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats.profit_factor.toFixed(2)}
                </span>
              </div>
              <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">利润因子</h3>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                平均盈利 / 平均亏损
              </p>
            </GlassCard>

            {/* Max Drawdown */}
            <GlassCard className="p-6">
              <div className="flex items-center justify-between mb-4">
                <AlertCircle className="text-orange-500" size={24} />
                <span className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats.max_drawdown ? `${(stats.max_drawdown * 100).toFixed(1)}%` : 'N/A'}
                </span>
              </div>
              <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">最大回撤</h3>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                风险指标
              </p>
            </GlassCard>
          </div>
        </>
      )}
    </div>
  );
};

export default PerformanceStats;
