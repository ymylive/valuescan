import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import {
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Users,
  BarChart3,
  Clock,
  Target,
  AlertCircle,
} from 'lucide-react'

interface SimTrader {
  id: string
  name: string
  initial_balance: number
  current_balance: number
  leverage: number
  enabled: boolean
  created_at: number
  confidence_threshold?: number
  buy_threshold?: number
  sell_threshold?: number
  max_position_pct?: number
  default_sl_pct?: number
  default_tp_pct?: number
  fee_rate?: number
}

interface SimPosition {
  id: string
  trader_id: string
  symbol: string
  side: 'LONG' | 'SHORT'
  entry_price: number
  quantity: number
  leverage: number
  take_profit: number | null
  stop_loss: number | null
  opened_at: number
  status: string
  unrealized_pnl: number
  current_price: number | null
  pyramiding_levels?: Array<{ price: number; ratio: number; executed: boolean }>
  trailing_stop_enabled?: boolean
  trailing_callback_pct?: number
  highest_price?: number | null
}

interface SimTrade {
  id: string
  symbol: string
  side: 'LONG' | 'SHORT'
  entry_price: number
  exit_price: number
  quantity: number
  realized_pnl: number
  exit_reason: string
  closed_at: number
}

interface SimMetrics {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  total_pnl: number
  avg_pnl: number
  max_drawdown: number
  sharpe_ratio: number
  profit_factor: number
}

export function SimulationPage() {
  const [traders, setTraders] = useState<SimTrader[]>([])
  const [selectedTrader, setSelectedTrader] = useState<SimTrader | null>(null)
  const [positions, setPositions] = useState<SimPosition[]>([])
  const [trades, setTrades] = useState<SimTrade[]>([])
  const [metrics, setMetrics] = useState<SimMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTraders = async () => {
    try {
      const data = await api.getSimulationTraders()
      setTraders(data)
      if (data.length > 0 && !selectedTrader) {
        setSelectedTrader(data[0])
      }
    } catch (e: any) {
      setError(e.message)
    }
  }

  const fetchTraderData = async (traderId: string) => {
    try {
      const [posData, tradeData, metricsData] = await Promise.all([
        api.getSimulationPositions(traderId),
        api.getSimulationTrades(traderId, 50),
        api.getSimulationMetrics(traderId),
      ])
      setPositions(posData)
      setTrades(tradeData)
      setMetrics(metricsData)
    } catch (e: any) {
      console.error('Failed to fetch trader data:', e)
    }
  }

  useEffect(() => {
    setLoading(true)
    fetchTraders().finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (selectedTrader) {
      fetchTraderData(selectedTrader.id)
      const interval = setInterval(
        () => fetchTraderData(selectedTrader.id),
        5000
      )
      return () => clearInterval(interval)
    }
  }, [selectedTrader])

  const formatPrice = (price: number) => {
    if (price >= 1000)
      return price.toLocaleString('en-US', { maximumFractionDigits: 2 })
    if (price >= 1) return price.toFixed(4)
    return price.toFixed(6)
  }

  const formatPnL = (pnl: number) => {
    const sign = pnl >= 0 ? '+' : ''
    return `${sign}${pnl.toFixed(2)}`
  }

  const formatTime = (timestamp: number) => {
    if (!timestamp) return '--'
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getPnLColor = (pnl: number) => {
    if (pnl > 0) return 'text-green-400'
    if (pnl < 0) return 'text-red-400'
    return 'text-gray-400'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0b0e11] pt-20 flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-[#F0B90B] animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0b0e11] pt-20 pb-8 px-3 sm:px-4">
      <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2 sm:gap-3">
              <BarChart3 className="w-6 h-6 sm:w-7 sm:h-7 text-[#F0B90B]" />
              模拟交易系统
            </h1>
            <p className="text-xs sm:text-sm text-gray-400 mt-1">
              模拟交易环境，测试和验证交易策略
            </p>
          </div>
          <button
            onClick={() => {
              fetchTraders()
              if (selectedTrader) fetchTraderData(selectedTrader.id)
            }}
            className="flex items-center justify-center gap-2 px-4 py-2 bg-[#F0B90B]/10 text-[#F0B90B] rounded-lg hover:bg-[#F0B90B]/20 transition-colors w-full sm:w-auto"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 sm:gap-6">
          {/* Traders List */}
          <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl">
            <div className="px-4 py-3 border-b border-[#2b3139]">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Users className="w-4 h-4 text-[#F0B90B]" />
                虚拟交易员
              </h2>
            </div>
            <div className="divide-y divide-[#2b3139] max-h-[400px] overflow-y-auto">
              {traders.length === 0 ? (
                <div className="px-4 py-8 text-center text-gray-500">
                  暂无交易员
                </div>
              ) : (
                traders.map((trader) => (
                  <div
                    key={trader.id}
                    onClick={() => setSelectedTrader(trader)}
                    className={`px-4 py-3 cursor-pointer transition-colors ${
                      selectedTrader?.id === trader.id
                        ? 'bg-[#F0B90B]/10 border-l-2 border-l-[#F0B90B]'
                        : 'hover:bg-[#2b3139]/50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <div className="font-medium text-white">
                            {trader.name}
                          </div>
                          {!trader.enabled && (
                            <span className="px-1 py-0.5 rounded text-[9px] bg-gray-500/20 text-gray-400">
                              已禁用
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-400 mt-0.5">
                          {trader.leverage}x · SL {trader.default_sl_pct || 2}%
                          · TP {trader.default_tp_pct || 5}%
                        </div>
                      </div>
                      <div className="text-right">
                        <div
                          className={`text-sm font-mono ${getPnLColor(trader.current_balance - trader.initial_balance)}`}
                        >
                          ${trader.current_balance.toFixed(2)}
                        </div>
                        <div className="text-xs text-gray-500">
                          初始: ${trader.initial_balance.toFixed(0)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3 space-y-6">
            {selectedTrader ? (
              <>
                {/* Trader Info Card */}
                <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-semibold text-white">
                      {selectedTrader.name}
                    </h3>
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        selectedTrader.enabled
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-gray-500/20 text-gray-400'
                      }`}
                    >
                      {selectedTrader.enabled ? '运行中' : '已禁用'}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3 text-sm">
                    <div>
                      <div className="text-gray-400 text-xs">杠杆</div>
                      <div className="text-white font-medium">
                        {selectedTrader.leverage}x
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400 text-xs">止损</div>
                      <div className="text-red-400 font-medium">
                        {selectedTrader.default_sl_pct || 2}%
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400 text-xs">止盈</div>
                      <div className="text-green-400 font-medium">
                        {selectedTrader.default_tp_pct || 5}%
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400 text-xs">最大仓位</div>
                      <div className="text-white font-medium">
                        {selectedTrader.max_position_pct || 10}%
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400 text-xs">买入阈值</div>
                      <div className="text-white font-medium">
                        {((selectedTrader.buy_threshold || 0.7) * 100).toFixed(
                          0
                        )}
                        %
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400 text-xs">手续费率</div>
                      <div className="text-white font-medium">
                        {((selectedTrader.fee_rate || 0.0004) * 100).toFixed(2)}
                        %
                      </div>
                    </div>
                  </div>
                </div>

                {/* Metrics Overview */}
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 sm:gap-4">
                  <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl p-4">
                    <div className="text-xs text-gray-400 mb-1">总交易</div>
                    <div className="text-xl font-bold text-white">
                      {metrics?.total_trades || 0}
                    </div>
                  </div>
                  <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl p-4">
                    <div className="text-xs text-gray-400 mb-1">胜率</div>
                    <div className="text-xl font-bold text-white">
                      {metrics?.win_rate
                        ? `${(metrics.win_rate * 100).toFixed(1)}%`
                        : '0%'}
                    </div>
                  </div>
                  <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl p-4">
                    <div className="text-xs text-gray-400 mb-1">总盈亏</div>
                    <div
                      className={`text-xl font-bold ${getPnLColor(metrics?.total_pnl || 0)}`}
                    >
                      ${formatPnL(metrics?.total_pnl || 0)}
                    </div>
                  </div>
                  <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl p-4">
                    <div className="text-xs text-gray-400 mb-1">最大回撤</div>
                    <div className="text-xl font-bold text-red-400">
                      $
                      {metrics?.max_drawdown
                        ? metrics.max_drawdown.toFixed(2)
                        : '0'}
                    </div>
                  </div>
                  <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl p-4">
                    <div className="text-xs text-gray-400 mb-1">盈亏比</div>
                    <div className="text-xl font-bold text-white">
                      {metrics?.profit_factor
                        ? metrics.profit_factor.toFixed(2)
                        : '0'}
                    </div>
                  </div>
                  <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl p-4">
                    <div className="text-xs text-gray-400 mb-1">夏普比率</div>
                    <div className="text-xl font-bold text-white">
                      {metrics?.sharpe_ratio
                        ? metrics.sharpe_ratio.toFixed(2)
                        : '0'}
                    </div>
                  </div>
                </div>

                {/* Open Positions */}
                <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl">
                  <div className="px-4 py-3 border-b border-[#2b3139] flex items-center justify-between">
                    <h3 className="text-base font-semibold text-white flex items-center gap-2">
                      <Target className="w-4 h-4 text-[#F0B90B]" />
                      持仓中 ({positions.length})
                    </h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="text-xs text-gray-400 border-b border-[#2b3139]">
                          <th className="text-left px-4 py-2">币种</th>
                          <th className="text-left px-4 py-2">方向</th>
                          <th className="text-right px-4 py-2">入场价</th>
                          <th className="text-right px-4 py-2">现价</th>
                          <th className="text-right px-4 py-2">数量</th>
                          <th className="text-right px-4 py-2">未实现盈亏</th>
                          <th className="text-right px-4 py-2">止盈/止损</th>
                          <th className="text-center px-4 py-2">策略</th>
                        </tr>
                      </thead>
                      <tbody>
                        {positions.length === 0 ? (
                          <tr>
                            <td
                              colSpan={8}
                              className="px-4 py-8 text-center text-gray-500"
                            >
                              暂无持仓
                            </td>
                          </tr>
                        ) : (
                          positions.map((pos) => (
                            <tr
                              key={pos.id}
                              className="border-b border-[#2b3139] hover:bg-[#2b3139]/30"
                            >
                              <td className="px-4 py-3 font-medium text-white">
                                {pos.symbol}
                              </td>
                              <td className="px-4 py-3">
                                <span
                                  className={`px-2 py-0.5 rounded text-xs font-bold ${
                                    pos.side === 'LONG'
                                      ? 'bg-green-500/20 text-green-400'
                                      : 'bg-red-500/20 text-red-400'
                                  }`}
                                >
                                  {pos.side}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-right font-mono text-gray-300">
                                ${formatPrice(pos.entry_price)}
                              </td>
                              <td className="px-4 py-3 text-right font-mono text-white">
                                $
                                {formatPrice(
                                  pos.current_price || pos.entry_price
                                )}
                              </td>
                              <td className="px-4 py-3 text-right font-mono text-gray-300">
                                {pos.quantity.toFixed(4)}
                              </td>
                              <td
                                className={`px-4 py-3 text-right font-mono font-medium ${getPnLColor(pos.unrealized_pnl)}`}
                              >
                                ${formatPnL(pos.unrealized_pnl)}
                              </td>
                              <td className="px-4 py-3 text-right text-xs text-gray-400">
                                <span className="text-green-400">
                                  {pos.take_profit
                                    ? `TP: $${formatPrice(pos.take_profit)}`
                                    : '-'}
                                </span>
                                <span className="mx-1">/</span>
                                <span className="text-red-400">
                                  {pos.stop_loss
                                    ? `SL: $${formatPrice(pos.stop_loss)}`
                                    : '-'}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-center">
                                <div className="flex items-center justify-center gap-1">
                                  {pos.pyramiding_levels &&
                                    pos.pyramiding_levels.length > 0 && (
                                      <span
                                        className="px-1.5 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-400"
                                        title={`金字塔止盈: ${pos.pyramiding_levels.filter((l) => l.executed).length}/${pos.pyramiding_levels.length}`}
                                      >
                                        🎯{' '}
                                        {
                                          pos.pyramiding_levels.filter(
                                            (l) => l.executed
                                          ).length
                                        }
                                        /{pos.pyramiding_levels.length}
                                      </span>
                                    )}
                                  {pos.trailing_stop_enabled && (
                                    <span
                                      className="px-1.5 py-0.5 rounded text-[10px] bg-blue-500/20 text-blue-400"
                                      title={`移动止损: ${pos.trailing_callback_pct}% 回调`}
                                    >
                                      📈 {pos.trailing_callback_pct}%
                                    </span>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Recent Trades */}
                <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl">
                  <div className="px-4 py-3 border-b border-[#2b3139]">
                    <h3 className="text-base font-semibold text-white flex items-center gap-2">
                      <Clock className="w-4 h-4 text-[#F0B90B]" />
                      最近交易
                    </h3>
                  </div>
                  <div className="divide-y divide-[#2b3139] max-h-[400px] overflow-y-auto">
                    {trades.length === 0 ? (
                      <div className="px-4 py-8 text-center text-gray-500">
                        暂无交易记录
                      </div>
                    ) : (
                      trades.map((trade) => (
                        <div
                          key={trade.id}
                          className="px-4 py-3 hover:bg-[#2b3139]/30"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div
                                className={`p-1.5 rounded ${
                                  trade.side === 'LONG'
                                    ? 'bg-green-500/20'
                                    : 'bg-red-500/20'
                                }`}
                              >
                                {trade.side === 'LONG' ? (
                                  <TrendingUp className="w-4 h-4 text-green-400" />
                                ) : (
                                  <TrendingDown className="w-4 h-4 text-red-400" />
                                )}
                              </div>
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="font-medium text-white">
                                    {trade.symbol}
                                  </span>
                                  <span
                                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                      trade.side === 'LONG'
                                        ? 'bg-green-500/20 text-green-400'
                                        : 'bg-red-500/20 text-red-400'
                                    }`}
                                  >
                                    {trade.side}
                                  </span>
                                </div>
                                <div className="text-xs text-gray-400 mt-0.5">
                                  {trade.exit_reason} •{' '}
                                  {formatTime(trade.closed_at)}
                                </div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div
                                className={`font-mono font-medium ${getPnLColor(trade.realized_pnl)}`}
                              >
                                ${formatPnL(trade.realized_pnl)}
                              </div>
                              <div className="text-xs text-gray-500">
                                ${formatPrice(trade.entry_price)} → $
                                {formatPrice(trade.exit_price)}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="bg-[#1e2329] border border-[#2b3139] rounded-xl p-12 text-center">
                <Users className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <div className="text-gray-400">选择一个交易员查看详情</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default SimulationPage
