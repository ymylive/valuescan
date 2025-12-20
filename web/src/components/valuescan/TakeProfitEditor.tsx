import { Target } from 'lucide-react'

interface TakeProfitLevel {
  percent: number
  ratio: number
}

interface TakeProfitEditorProps {
  levels: TakeProfitLevel[]
  onChange: (levels: TakeProfitLevel[]) => void
  stopLossPercent?: number
  onStopLossChange?: (value: number) => void
}

export function TakeProfitEditor({
  levels,
  onChange,
  stopLossPercent,
  onStopLossChange,
}: TakeProfitEditorProps) {
  // Ensure we have exactly 3 levels
  const normalizedLevels: TakeProfitLevel[] = [
    levels[0] || { percent: 3, ratio: 0.5 },
    levels[1] || { percent: 5, ratio: 0.5 },
    levels[2] || { percent: 8, ratio: 1.0 },
  ]

  const handlePercentChange = (index: number, value: string) => {
    const num = parseFloat(value)
    if (isNaN(num)) return
    const newLevels = [...normalizedLevels]
    newLevels[index] = { ...newLevels[index], percent: num }
    onChange(newLevels)
  }

  const handleRatioChange = (index: number, value: string) => {
    const num = parseFloat(value)
    if (isNaN(num) || num < 0 || num > 1) return
    const newLevels = [...normalizedLevels]
    newLevels[index] = { ...newLevels[index], ratio: num }
    onChange(newLevels)
  }

  const levelLabels = ['第一目标', '第二目标', '第三目标']
  const levelColors = ['text-yellow-500', 'text-orange-500', 'text-green-500']

  return (
    <div className="space-y-4">
      {/* Stop Loss */}
      {stopLossPercent !== undefined && onStopLossChange && (
        <div className="glass-panel rounded-lg p-4 bg-red-500/5 border-red-500/10">
          <div className="flex items-center gap-2 mb-3">
            <div className="status-dot text-red-500 bg-red-500" />
            <span className="text-sm font-medium text-white">止损设置</span>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-neutral-400 w-24">亏损百分比</label>
            <div className="relative flex-1 max-w-32 group">
              <input
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={stopLossPercent}
                onChange={(e) =>
                  onStopLossChange(parseFloat(e.target.value) || 0)
                }
                className="input-modern pr-8 border-red-500/20 focus:border-red-500/40"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 text-sm">
                %
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Take Profit Levels */}
      <div className="glass-panel rounded-lg p-4 bg-white/5">
        <div className="flex items-center gap-2 mb-4">
          <Target className="w-4 h-4 text-neutral-400" />
          <span className="text-sm font-medium text-white">分批止盈 (金字塔)</span>
        </div>

        <div className="space-y-4">
          {normalizedLevels.map((level, index) => (
            <div key={index} className="flex items-center gap-4 flex-wrap p-3 rounded-lg bg-black/20 border border-white/5">
              <div className="flex items-center gap-2 w-24">
                <div
                  className={`status-dot ${levelColors[index].replace('text-', 'bg-')} ${levelColors[index]}`}
                />
                <span className={`text-sm font-medium ${levelColors[index]}`}>
                  {levelLabels[index]}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <label className="text-xs text-neutral-500">盈利</label>
                <div className="relative w-24">
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={level.percent}
                    onChange={(e) => handlePercentChange(index, e.target.value)}
                    className="input-modern px-2 py-1.5 pr-6 text-xs h-8"
                  />
                  <span className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 text-[10px]">
                    %
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <label className="text-xs text-neutral-500">平仓</label>
                <div className="relative w-24">
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    value={level.ratio}
                    onChange={(e) => handleRatioChange(index, e.target.value)}
                    className="input-modern px-2 py-1.5 pr-6 text-xs h-8"
                  />
                  <span className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 text-[10px]">
                    ×
                  </span>
                </div>
              </div>

              <span className="text-[10px] text-neutral-500 font-mono">
                ({Math.round(level.ratio * 100)}% POSITION)
              </span>
            </div>
          ))}
        </div>

        <div className="mt-4 pt-3 border-t border-white/5">
          <p className="text-[10px] text-neutral-500 leading-relaxed italic">
            * 提示：平仓比例为剩余仓位的百分比。例如 0.5 表示平掉剩余仓位的 50%。
          </p>
        </div>
      </div>
    </div>
  )
}
