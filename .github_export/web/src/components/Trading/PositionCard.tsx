import React, { useState } from 'react';
import { GlassCard } from '../Common/GlassCard';
import { Button } from '../Common/Button';
import { Position } from '../../types/trading';
import { TrendingUp, TrendingDown, X } from 'lucide-react';
import toast from 'react-hot-toast';

interface PositionCardProps {
  position: Position;
  traderId: string;
  onClose?: (symbol: string, side: string) => void;
}

export const PositionCard: React.FC<PositionCardProps> = ({
  position,
  traderId,
  onClose,
}) => {
  const [closing, setClosing] = useState(false);

  const isProfit = position.unrealized_pnl > 0;
  const pnlColor = isProfit ? 'text-green-500' : 'text-red-500';
  const bgColor = isProfit
    ? 'bg-green-100 dark:bg-green-900/30'
    : 'bg-red-100 dark:bg-red-900/30';

  const handleClose = async () => {
    if (!onClose) return;

    if (!window.confirm(`Close ${position.side} position for ${position.symbol}?`)) {
      return;
    }

    setClosing(true);
    try {
      await onClose(position.symbol, position.side);
      toast.success('Position closed successfully');
    } catch (error) {
      toast.error('Failed to close position');
      console.error('Close position error:', error);
    } finally {
      setClosing(false);
    }
  };

  return (
    <GlassCard animate hover className="p-4">
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-2">
          {position.side === 'LONG' ? (
            <TrendingUp size={20} className="text-green-500" />
          ) : (
            <TrendingDown size={20} className="text-red-500" />
          )}
          <div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">
              {position.symbol}
            </h3>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {position.side} • {position.leverage}x
            </span>
          </div>
        </div>
        {onClose && (
          <button
            onClick={handleClose}
            disabled={closing}
            className="p-1 text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50"
          >
            <X size={18} />
          </button>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500 dark:text-gray-400">Entry Price</span>
          <span className="font-mono font-medium dark:text-white">
            ${position.entry_price.toFixed(2)}
          </span>
        </div>

        <div className="flex justify-between text-sm">
          <span className="text-gray-500 dark:text-gray-400">Mark Price</span>
          <span className="font-mono font-medium dark:text-white">
            ${position.mark_price.toFixed(2)}
          </span>
        </div>

        <div className="flex justify-between text-sm">
          <span className="text-gray-500 dark:text-gray-400">Size</span>
          <span className="font-mono font-medium dark:text-white">
            {position.size.toFixed(4)}
          </span>
        </div>

        <div className={`flex justify-between text-sm p-2 rounded-lg ${bgColor}`}>
          <span className="font-medium">Unrealized PnL</span>
          <div className="text-right">
            <div className={`font-mono font-bold ${pnlColor}`}>
              ${position.unrealized_pnl.toFixed(2)}
            </div>
            <div className={`text-xs ${pnlColor}`}>
              ({position.unrealized_pnl_pct > 0 ? '+' : ''}
              {position.unrealized_pnl_pct.toFixed(2)}%)
            </div>
          </div>
        </div>

        {position.duration && (
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
            <span>Duration</span>
            <span>{position.duration}</span>
          </div>
        )}

        {position.liquidation_price && (
          <div className="flex justify-between text-xs text-amber-600 dark:text-amber-400">
            <span>Liquidation Price</span>
            <span className="font-mono">${position.liquidation_price.toFixed(2)}</span>
          </div>
        )}
      </div>
    </GlassCard>
  );
};
