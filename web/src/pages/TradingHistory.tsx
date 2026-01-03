import React, { useState, useEffect } from 'react';
import { History, Filter, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { GlassCard } from '../components/Common/GlassCard';
import { Button } from '../components/Common/Button';
import { Decision } from '../types/trading';
import { tradingApi } from '../services/tradingApi';
import { logger } from '../services/loggerService';

const TradingHistory: React.FC = () => {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedTrader, setSelectedTrader] = useState<string>('all');
  const [selectedAction, setSelectedAction] = useState<string>('all');
  const [searchSymbol, setSearchSymbol] = useState<string>('');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 50;

  useEffect(() => {
    loadDecisions();
  }, []);

  const loadDecisions = async () => {
    setLoading(true);
    setError(null);
    logger.info('TradingHistory', '开始加载交易历史', {
      trader: selectedTrader,
      action: selectedAction,
      searchSymbol: searchSymbol
    });
    try {
      const response = await tradingApi.getDecisions(selectedTrader === 'all' ? '' : selectedTrader);
      setDecisions(response.data);
      logger.info('TradingHistory', '交易历史加载成功', {
        count: response.data.length,
        trader: selectedTrader,
        firstDecision: response.data[0] || null,
        lastDecision: response.data[response.data.length - 1] || null
      });
    } catch (err) {
      setError('加载交易历史失败');
      logger.error('TradingHistory', '加载交易历史失败', err as Error, {
        trader: selectedTrader,
        action: selectedAction,
        errorDetails: err
      });
      console.error('Failed to load decisions:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <History className="text-blue-500" size={32} />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">交易历史</h2>
        </div>
        <Button
          onClick={loadDecisions}
          disabled={loading}
          className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600"
        >
          刷新
        </Button>
      </div>

      {/* Filters */}
      <GlassCard className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Trader Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              交易者
            </label>
            <select
              value={selectedTrader}
              onChange={(e) => setSelectedTrader(e.target.value)}
              className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg"
            >
              <option value="all">全部</option>
            </select>
          </div>

          {/* Action Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              操作类型
            </label>
            <select
              value={selectedAction}
              onChange={(e) => setSelectedAction(e.target.value)}
              className="w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg"
            >
              <option value="all">全部</option>
              <option value="OPEN">开仓</option>
              <option value="CLOSE">平仓</option>
              <option value="HOLD">持有</option>
            </select>
          </div>

          {/* Symbol Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              币种搜索
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                value={searchSymbol}
                onChange={(e) => setSearchSymbol(e.target.value)}
                placeholder="输入币种名称..."
                className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg"
              />
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 rounded-lg">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      )}

      {/* Decisions Table */}
      {!loading && !error && (
        <GlassCard className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    时间
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    交易者
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    币种
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    操作
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    价格
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    数量
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    盈亏
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    原因
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {decisions.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                      暂无交易历史
                    </td>
                  </tr>
                ) : (
                  decisions.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage).map((decision) => (
                    <tr key={decision.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        {new Date(decision.timestamp).toLocaleString('zh-CN')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        {decision.trader_id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                        {decision.symbol}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          decision.action === 'OPEN' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200' :
                          decision.action === 'CLOSE' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200' :
                          'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-200'
                        }`}>
                          {decision.action}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        {decision.price ? `$${decision.price.toFixed(2)}` : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        {decision.size ? decision.size.toFixed(4) : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {decision.pnl !== undefined ? (
                          <span className={decision.pnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                            ${decision.pnl.toFixed(2)} ({decision.pnl_pct?.toFixed(2)}%)
                          </span>
                        ) : '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 max-w-xs truncate">
                        {decision.reason}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {decisions.length > itemsPerPage && (
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div className="text-sm text-gray-700 dark:text-gray-300">
                显示 {(currentPage - 1) * itemsPerPage + 1} - {Math.min(currentPage * itemsPerPage, decisions.length)} 条，共 {decisions.length} 条
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="flex items-center gap-1 bg-gray-500 hover:bg-gray-600 disabled:opacity-50"
                >
                  <ChevronLeft size={18} />
                  上一页
                </Button>
                <Button
                  onClick={() => setCurrentPage(p => Math.min(Math.ceil(decisions.length / itemsPerPage), p + 1))}
                  disabled={currentPage >= Math.ceil(decisions.length / itemsPerPage)}
                  className="flex items-center gap-1 bg-gray-500 hover:bg-gray-600 disabled:opacity-50"
                >
                  下一页
                  <ChevronRight size={18} />
                </Button>
              </div>
            </div>
          )}
        </GlassCard>
      )}
    </div>
  );
};

export default TradingHistory;
