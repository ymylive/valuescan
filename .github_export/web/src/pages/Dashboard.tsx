import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Activity, AlertTriangle, Database, Radar, DollarSign, Users, TrendingUp, Target } from 'lucide-react';
import { GlassCard } from '../components/Common/GlassCard';
import { StatCard } from '../components/Trading/StatCard';
import { PositionCard } from '../components/Trading/PositionCard';
import ValuScanDataPanel from '../components/Config/ValuScanDataPanel';
import ErrorBoundary from '../components/Common/ErrorBoundary';
import api from '../services/api';
import { tradingApi } from '../services/tradingApi';
import { TraderConfig, AccountInfo, Position, Decision } from '../types/trading';

interface DbStats {
  by_type?: Record<string, number>;
  earliest?: number;
  latest?: number;
  total?: number;
}

interface DbStatus {
  available: boolean;
  stats?: DbStats;
}

interface SignalItem {
  id: number | string;
  type: string;
  symbol: string;
  title: string;
  timestamp: number | string;
}

// Removed old StatCard - now using imported StatCard component

const formatTimestamp = (value?: number | string) => {
  if (!value && value !== 0) return '-';
  const numeric = typeof value === 'string' ? Number(value) : value;
  if (!Number.isFinite(numeric)) return '-';
  const ms = numeric < 1e12 ? numeric * 1000 : numeric;
  return new Date(ms).toLocaleString();
};

const Dashboard: React.FC = () => {
  const { t } = useTranslation();
  const [dbStatus, setDbStatus] = useState<DbStatus | null>(null);
  const [signals, setSignals] = useState<SignalItem[]>([]);
  const [alerts, setAlerts] = useState<SignalItem[]>([]);
  const [loading, setLoading] = useState(true);

  // AI Trading states
  const [traders, setTraders] = useState<TraderConfig[]>([]);
  const [tradingData, setTradingData] = useState({
    totalEquity: 0,
    activeTraders: 0,
    totalPnL: 0,
    winRate: 0,
  });
  const [positions, setPositions] = useState<Position[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      const results = await Promise.allSettled([
        api.get<DbStatus>('/db/status'),
        api.get<{ signals: SignalItem[] }>('/signals', { params: { limit: 5 } }),
        api.get<{ alerts: SignalItem[] }>('/alerts', { params: { limit: 5 } }),
      ]);

      if (results[0].status === 'fulfilled') {
        const status = results[0].value as unknown as DbStatus;
        setDbStatus(status);
      } else {
        setDbStatus(null);
      }

      if (results[1].status === 'fulfilled') {
        const payload = results[1].value as unknown as { signals?: SignalItem[] };
        setSignals(payload?.signals || []);
      } else {
        setSignals([]);
      }

      if (results[2].status === 'fulfilled') {
        const payload = results[2].value as unknown as { alerts?: SignalItem[] };
        setAlerts(payload?.alerts || []);
      } else {
        setAlerts([]);
      }

      setLoading(false);
    };

    loadData();
  }, []);

  // Load AI Trading data with polling
  useEffect(() => {
    const loadTradingData = async () => {
      try {
        // Get all traders
        const allTraders = (await tradingApi.getTraders()) as unknown as TraderConfig[];
        setTraders(allTraders || []);

        // Filter running traders
        const runningTraders = (allTraders || []).filter((t: TraderConfig) => t.is_running);

        if (runningTraders.length === 0) {
          setTradingData({
            totalEquity: 0,
            activeTraders: 0,
            totalPnL: 0,
            winRate: 0,
          });
          setPositions([]);
          setDecisions([]);
          return;
        }

        // Fetch account info for all running traders
        const accountPromises = runningTraders.map((t: TraderConfig) =>
          tradingApi.getAccount(t.trader_id).catch(() => null)
        );
        const accounts = await Promise.all(accountPromises);

        // Aggregate trading data
        let totalEquity = 0;
        let totalPnL = 0;
        let totalTrades = 0;
        let winningTrades = 0;

        accounts.forEach((acc) => {
          if (acc) {
            const accountInfo = acc as unknown as AccountInfo;
            totalEquity += accountInfo.total_equity || 0;
            totalPnL += accountInfo.total_pnl || 0;
          }
        });

        // Fetch positions (top 5)
        const positionPromises = runningTraders.slice(0, 3).map((t: TraderConfig) =>
          tradingApi.getPositions(t.trader_id).catch(() => [])
        );
        const allPositions = await Promise.all(positionPromises);
        const flatPositions = (allPositions.flat() as unknown as Position[]).slice(0, 5);
        setPositions(flatPositions);

        // Fetch latest decisions (top 5)
        const decisionPromises = runningTraders.slice(0, 3).map((t: TraderConfig) =>
          tradingApi.getLatestDecisions(t.trader_id, 2).catch(() => [])
        );
        const allDecisions = await Promise.all(decisionPromises);
        const flatDecisions = (allDecisions.flat() as unknown as Decision[]).slice(0, 5);
        setDecisions(flatDecisions);

        setTradingData({
          totalEquity,
          activeTraders: runningTraders.length,
          totalPnL,
          winRate: totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0,
        });
      } catch (error) {
        console.error('Failed to load trading data:', error);
      }
    };

    loadTradingData();
    const interval = setInterval(loadTradingData, 10000); // 10 seconds

    return () => clearInterval(interval);
  }, []);

  const byType = dbStatus?.stats?.by_type || {};
  const totalMessages = dbStatus?.stats?.total ?? 0;
  const signalCount = (byType['110'] || 0) + (byType['113'] || 0);
  const alertCount = byType['112'] || 0;

  // Telegram signal stats
  const telegramStats = useMemo(() => [
    {
      title: 'Messages',
      value: totalMessages.toString(),
      icon: Database,
      color: 'text-green-500',
      subtitle: dbStatus?.available ? 'DB online' : 'DB unavailable',
    },
    {
      title: 'Signals',
      value: signalCount.toString(),
      icon: Radar,
      color: 'text-blue-500',
      subtitle: 'ALPHA + FOMO',
    },
    {
      title: 'Alerts',
      value: alertCount.toString(),
      icon: AlertTriangle,
      color: 'text-amber-500',
      subtitle: 'Risk signals',
    },
    {
      title: 'Last Update',
      value: formatTimestamp(dbStatus?.stats?.latest),
      icon: Activity,
      color: 'text-purple-500',
    },
  ], [totalMessages, signalCount, alertCount, dbStatus]);

  // AI Trading stats
  const aiTradingStats = useMemo(() => [
    {
      title: 'Total Equity',
      value: `$${tradingData.totalEquity.toFixed(2)}`,
      icon: DollarSign,
      color: 'text-green-500',
      subtitle: `${traders.length} traders`,
      trend: tradingData.totalPnL > 0 ? 'up' as const : tradingData.totalPnL < 0 ? 'down' as const : 'neutral' as const,
    },
    {
      title: 'Active Traders',
      value: tradingData.activeTraders.toString(),
      icon: Users,
      color: 'text-blue-500',
      subtitle: 'Running now',
    },
    {
      title: 'Total PnL',
      value: `$${tradingData.totalPnL.toFixed(2)}`,
      icon: TrendingUp,
      color: tradingData.totalPnL >= 0 ? 'text-green-500' : 'text-red-500',
      subtitle: `${tradingData.totalPnL >= 0 ? '+' : ''}${((tradingData.totalPnL / (tradingData.totalEquity - tradingData.totalPnL || 1)) * 100).toFixed(2)}%`,
      trend: tradingData.totalPnL > 0 ? 'up' as const : tradingData.totalPnL < 0 ? 'down' as const : 'neutral' as const,
    },
    {
      title: 'Win Rate',
      value: `${tradingData.winRate.toFixed(1)}%`,
      icon: Target,
      color: 'text-purple-500',
      subtitle: 'Overall',
    },
  ], [tradingData, traders]);

  const renderList = (items: SignalItem[], emptyLabel: string) => (
    <div className="space-y-3 overflow-y-auto h-[calc(100%-2rem)]">
      {items.length === 0 ? (
        <div className="text-sm text-gray-500">{emptyLabel}</div>
      ) : (
        items.map((item) => (
          <div
            key={item.id}
            className="flex items-center gap-3 p-2 rounded-lg bg-white/50 dark:bg-white/5"
          >
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                [{item.type}] {item.symbol} {item.title}
              </p>
              <p className="text-xs text-gray-500">{formatTimestamp(item.timestamp)}</p>
            </div>
          </div>
        ))
      )}
    </div>
  );

  if (loading) {
    return <div className="p-8 text-center text-gray-500">{t('common.loading')}</div>;
  }

  return (
    <div className="space-y-6">
      {/* Telegram Signals Section */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Telegram Signals
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          {telegramStats.map((stat, index) => (
            <StatCard key={stat.title} {...stat} index={index} />
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 mt-6">
          <GlassCard className="p-6 h-96 animate-slide-up">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Recent Signals</h3>
            {renderList(signals, 'No signals yet')}
          </GlassCard>

          <GlassCard className="p-6 h-96 animate-slide-up" style={{ animationDelay: '100ms' }}>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Recent Alerts</h3>
            {renderList(alerts, 'No alerts yet')}
          </GlassCard>
        </div>
      </div>

      {/* AI Trading Section */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          AI Trading Overview
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          {aiTradingStats.map((stat, index) => (
            <StatCard key={stat.title} {...stat} index={index} />
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 mt-6">
          <GlassCard className="p-6 h-96 animate-slide-up">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
              Active Positions ({positions.length})
            </h3>
            <div className="space-y-3 overflow-y-auto h-[calc(100%-2rem)]">
              {positions.length === 0 ? (
                <div className="text-sm text-gray-500">No active positions</div>
              ) : (
                positions.map((position, idx) => (
                  <div key={`${position.symbol}-${idx}`} className="scale-90 origin-top">
                    <PositionCard position={position} traderId="" />
                  </div>
                ))
              )}
            </div>
          </GlassCard>

          <GlassCard className="p-6 h-96 animate-slide-up" style={{ animationDelay: '100ms' }}>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
              Latest Decisions ({decisions.length})
            </h3>
            <div className="space-y-3 overflow-y-auto h-[calc(100%-2rem)]">
              {decisions.length === 0 ? (
                <div className="text-sm text-gray-500">No recent decisions</div>
              ) : (
                decisions.map((decision) => (
                  <div
                    key={decision.id}
                    className="flex items-center gap-3 p-3 rounded-lg bg-white/50 dark:bg-white/5"
                  >
                    <div className="w-2 h-2 rounded-full bg-blue-500" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                        {decision.action} {decision.symbol}
                      </p>
                      <p className="text-xs text-gray-500">{decision.reason.slice(0, 60)}...</p>
                      <p className="text-xs text-gray-400 mt-1">
                        {formatTimestamp(decision.timestamp)}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </GlassCard>
        </div>
      </div>

      {/* ValuScan Data Section */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          ValuScan 市场数据
        </h2>
        <ErrorBoundary>
          <ValuScanDataPanel defaultSymbol="BTC" defaultKeyword={1} />
        </ErrorBoundary>
      </div>
    </div>
  );
};

export default React.memo(Dashboard);
