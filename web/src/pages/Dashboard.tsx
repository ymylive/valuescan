import React, { useMemo } from 'react';
import { GlassCard } from '../components/Common/GlassCard';
import { useTranslation } from 'react-i18next';
import { TrendingUp, Users, DollarSign, Activity } from 'lucide-react';

const StatCard = React.memo<{
  title: string;
  value: string;
  icon: React.ElementType;
  change: string;
  color: string;
  index: number;
}>(({ title, value, icon: Icon, change, color, index }) => (
  <GlassCard
    animate
    hover
    className="p-6 flex items-center justify-between"
    style={{ animationDelay: `${index * 100}ms` }}
  >
    <div>
      <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">{title}</p>
      <h3 className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value}</h3>
      <span className={`text-xs font-medium ${change.startsWith('+') ? 'text-green-500' : 'text-red-500'}`}>
        {change}
      </span>
    </div>
    <div className={`p-3 rounded-full bg-opacity-10 dark:bg-opacity-20 ${color.replace('text-', 'bg-')}`}>
      <Icon size={24} className={color} />
    </div>
  </GlassCard>
));

StatCard.displayName = 'StatCard';

const ActivityItem = React.memo(() => (
  <div className="flex items-center gap-3 p-2 hover:bg-white/5 rounded-lg smooth-transition touch-manipulation">
    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
    <div className="flex-1">
      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">Trader Alpha bought BTC</p>
      <p className="text-xs text-gray-500">2 mins ago</p>
    </div>
  </div>
));

ActivityItem.displayName = 'ActivityItem';

const Dashboard: React.FC = () => {
  const { t } = useTranslation();

  const stats = useMemo(() => [
    { title: t('dashboard.totalEquity'), value: '$12,345.67', icon: DollarSign, change: '+5.2%', color: 'text-green-500' },
    { title: t('dashboard.activeTraders'), value: '3', icon: Users, change: '0', color: 'text-blue-500' },
    { title: t('dashboard.totalPnL'), value: '+$1,234.56', icon: TrendingUp, change: '+12.4%', color: 'text-emerald-500' },
    { title: t('dashboard.winRate'), value: '68%', icon: Activity, change: '+2.1%', color: 'text-purple-500' },
  ], [t]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        {stats.map((stat, index) => (
          <StatCard key={stat.title} {...stat} index={index} />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        <GlassCard className="lg:col-span-2 p-6 h-96 animate-slide-up">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Equity History</h3>
          <div className="flex items-center justify-center h-full text-gray-500">
            Chart Placeholder
          </div>
        </GlassCard>

        <GlassCard className="p-6 h-96 animate-slide-up" style={{ animationDelay: '100ms' }}>
          <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Recent Activity</h3>
          <div className="space-y-4 overflow-y-auto h-[calc(100%-2rem)]">
            {[1, 2, 3, 4, 5].map((i) => (
              <ActivityItem key={i} />
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
};

export default React.memo(Dashboard);
