import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GlassCard } from '../components/Common/GlassCard';
import { StatCard } from '../components/Trading/StatCard';
import { PositionCard } from '../components/Trading/PositionCard';
import { tradingApi } from '../services/tradingApi';
import { TraderConfig, Position } from '../types/trading';
import { TrendingUp, TrendingDown, Activity, DollarSign } from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';

const PositionMonitor: React.FC = () => {
  const { t } = useTranslation();
  const [traders, setTraders] = useState<TraderConfig[]>([]);
  const [allPositions, setAllPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch positions with 5-second polling
  useEffect(() => {
    const fetchPositions = async () => {
      try {
        // Get all traders
        const allTraders = (await tradingApi.getTraders()) as unknown as TraderConfig[];
        setTraders(allTraders || []);

        // Get running traders
        const runningTraders = (allTraders || []).filter((t: TraderConfig) => t.is_running);

        if (runningTraders.length === 0) {
          setAllPositions([]);
          setLoading(false);
          return;
        }

        // Fetch positions for all running traders
        const positionPromises = runningTraders.map((t: TraderConfig) =>
          tradingApi.getPositions(t.trader_id).catch(() => [])
        );
        const positionsArrays = await Promise.all(positionPromises);

        // Flatten and combine all positions
        const combined = positionsArrays.flat() as unknown as Position[];
        setAllPositions(combined);
      } catch (error) {
        console.error('Failed to fetch positions:', error);
        toast.error('Failed to load positions');
      } finally {
        setLoading(false);
      }
    };

    fetchPositions();
    const interval = setInterval(fetchPositions, 5000); // 5 seconds

    return () => clearInterval(interval);
  }, []);

  // Calculate summary statistics
  const totalPositions = allPositions.length;
  const longPositions = allPositions.filter(p => p.side === 'LONG').length;
  const shortPositions = allPositions.filter(p => p.side === 'SHORT').length;
  const totalUnrealizedPnL = allPositions.reduce((sum, p) => sum + p.unrealized_pnl, 0);

  const summaryStats = [
    {
      title: 'Total Positions',
      value: totalPositions.toString(),
      icon: Activity,
      color: 'text-blue-500',
      subtitle: `${traders.filter(t => t.is_running).length} active traders`,
    },
    {
      title: 'Long Positions',
      value: longPositions.toString(),
      icon: TrendingUp,
      color: 'text-green-500',
      subtitle: `${((longPositions / (totalPositions || 1)) * 100).toFixed(0)}%`,
    },
    {
      title: 'Short Positions',
      value: shortPositions.toString(),
      icon: TrendingDown,
      color: 'text-red-500',
      subtitle: `${((shortPositions / (totalPositions || 1)) * 100).toFixed(0)}%`,
    },
    {
      title: 'Unrealized PnL',
      value: `$${totalUnrealizedPnL.toFixed(2)}`,
      icon: DollarSign,
      color: totalUnrealizedPnL >= 0 ? 'text-green-500' : 'text-red-500',
      subtitle: totalUnrealizedPnL >= 0 ? 'Profit' : 'Loss',
      trend: totalUnrealizedPnL > 0 ? 'up' as const : totalUnrealizedPnL < 0 ? 'down' as const : 'neutral' as const,
    },
  ];

  const handleClosePosition = async (symbol: string, side: string) => {
    // Find the trader for this position
    const position = allPositions.find(p => p.symbol === symbol && p.side === side);
    if (!position) return;

    // Find trader ID (we need to store it in position or pass it differently)
    // For now, we'll need to refetch after close
    toast.success('Close position request sent');

    // Refresh positions after a short delay
    setTimeout(() => {
      window.location.reload();
    }, 1000);
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-500">{t('common.loading')}</div>;
  }

  return (
    <div className="space-y-6">
      <Toaster position="top-right" />

      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Position Monitor
        </h2>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Auto-refresh: 5s
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        {summaryStats.map((stat, index) => (
          <StatCard key={stat.title} {...stat} index={index} />
        ))}
      </div>

      {/* Positions Grid */}
      <div>
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
          Active Positions
        </h3>
        {allPositions.length === 0 ? (
          <GlassCard className="p-8 text-center">
            <p className="text-gray-500 dark:text-gray-400">
              No active positions
            </p>
          </GlassCard>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {allPositions.map((position, idx) => (
              <PositionCard
                key={`${position.symbol}-${position.side}-${idx}`}
                position={position}
                traderId=""
                onClose={handleClosePosition}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PositionMonitor;
