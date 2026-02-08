import { ReactNode, CSSProperties } from 'react';
import { cn } from '../../utils/cn';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}

export const GlassCard = ({ children, className, style }: GlassCardProps) => {
  return (
    <div
      style={style}
      className={cn(
        'rounded-xl backdrop-blur-md',
        'bg-white/70 dark:bg-gray-800/70',
        'border border-white/20 dark:border-gray-700/50',
        'shadow-lg',
        className
      )}
    >
      {children}
    </div>
  );
};
