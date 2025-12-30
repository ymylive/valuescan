import React from 'react';
import { GlassCard } from '../Common/GlassCard';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon: React.ElementType;
  color?: string;
  index?: number;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  icon: Icon,
  color = 'text-blue-500',
  index = 0,
}) => {
  const getTrendIcon = () => {
    if (!trend) return null;

    switch (trend) {
      case 'up':
        return <TrendingUp size={16} className="text-green-500" />;
      case 'down':
        return <TrendingDown size={16} className="text-red-500" />;
      case 'neutral':
        return <Minus size={16} className="text-gray-500" />;
      default:
        return null;
    }
  };

  return (
    <GlassCard
      animate
      hover
      className="p-6 flex items-center justify-between"
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div className="flex-1">
        <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">
          {title}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
            {value}
          </h3>
          {getTrendIcon()}
        </div>
        {subtitle && (
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1 block">
            {subtitle}
          </span>
        )}
      </div>
      <div
        className={`p-3 rounded-full bg-opacity-10 dark:bg-opacity-20 ${color.replace(
          'text-',
          'bg-'
        )}`}
      >
        <Icon size={24} className={color} />
      </div>
    </GlassCard>
  );
};
