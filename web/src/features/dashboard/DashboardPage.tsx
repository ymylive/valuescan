import { useTranslation } from 'react-i18next';
import { Database, Radar, AlertTriangle, Activity } from 'lucide-react';
import { PageContainer } from '../../components/layout';
import { StatCard, GlassCard } from '../../components/shared';
import { Spinner } from '../../components/ui';
import { useDashboardData } from './hooks/useDashboardData';

const formatTimestamp = (value?: number | string) => {
  if (!value && value !== 0) return '-';
  const numeric = typeof value === 'string' ? Number(value) : value;
  if (!Number.isFinite(numeric)) return '-';
  const ms = numeric < 1e12 ? numeric * 1000 : numeric;
  return new Date(ms).toLocaleString();
};

interface SignalItem {
  id: number | string;
  type: string;
  symbol: string;
  title: string;
  timestamp: number | string;
}

const SignalList = ({ items, emptyLabel }: { items: SignalItem[]; emptyLabel: string }) => (
  <div className="space-y-3 overflow-y-auto h-[calc(100%-2rem)]">
    {items.length === 0 ? (
      <div className="text-sm text-gray-500">{emptyLabel}</div>
    ) : (
      items.map((item) => (
        <div key={item.id} className="flex items-center gap-3 p-2 rounded-lg bg-white/50 dark:bg-white/5">
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

export const DashboardPage = () => {
  const { t } = useTranslation();
  const { dbStatus, signals, alerts, alertsDisabled, loading, totalMessages, signalCount, alertCount } = useDashboardData();

  if (loading) {
    return (
      <PageContainer className="flex items-center justify-center h-full">
        <Spinner size="lg" />
      </PageContainer>
    );
  }

  const stats = [
    {
      title: '消息总数',
      value: totalMessages,
      icon: <Database className="w-5 h-5" />,
    },
    {
      title: '信号总数',
      value: signalCount,
      icon: <Radar className="w-5 h-5" />,
    },
    {
      title: '预警总数',
      value: alertCount,
      icon: <AlertTriangle className="w-5 h-5" />,
    },
    {
      title: '最新时间',
      value: formatTimestamp(dbStatus?.stats?.latest),
      icon: <Activity className="w-5 h-5" />,
    },
  ];

  return (
    <PageContainer>
      <div className="space-y-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">运行概览</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat) => (
            <StatCard key={stat.title} {...stat} />
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <GlassCard className="p-6 h-96">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">最新信号</h3>
            <SignalList items={signals} emptyLabel="暂无信号" />
          </GlassCard>

          <GlassCard className="p-6 h-96">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">最新预警</h3>
            <SignalList items={alerts} emptyLabel={alertsDisabled ? '???????' : '????'} />
          </GlassCard>
        </div>
      </div>
    </PageContainer>
  );
};

export default DashboardPage;
