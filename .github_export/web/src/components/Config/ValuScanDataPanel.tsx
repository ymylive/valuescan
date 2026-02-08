import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import valuescanApi, {
  DenseAreaPoint,
  CoinRankItem,
  SignalItem,
  WhaleFlowItem,
  SymbolMap,
} from '../../services/valuescanApi';

interface ValuScanDataPanelProps {
  defaultSymbol?: string;
  defaultKeyword?: number;
}

type TabType = 'mainForce' | 'rankings' | 'signals' | 'whaleFlow';

const COMMON_COINS = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'DOGE', 'ADA', 'LINK', 'AVAX', 'DOT'];

const ValuScanDataPanel: React.FC<ValuScanDataPanelProps> = ({
  defaultSymbol = 'BTC',
  defaultKeyword = 1,
}) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabType>('mainForce');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 币种选择
  const [selectedSymbol, setSelectedSymbol] = useState(defaultSymbol);
  const [selectedKeyword, setSelectedKeyword] = useState(defaultKeyword);
  const [symbolMap, setSymbolMap] = useState<SymbolMap>({});
  const [customSymbol, setCustomSymbol] = useState('');

  // Main Force data
  const [denseAreas, setDenseAreas] = useState<DenseAreaPoint[]>([]);
  const [currentDensePrice, setCurrentDensePrice] = useState<number | null>(null);
  const [currentHoldCost, setCurrentHoldCost] = useState<number | null>(null);

  // Rankings data
  const [gainers, setGainers] = useState<CoinRankItem[]>([]);
  const [losers, setLosers] = useState<CoinRankItem[]>([]);
  const [mainCostRank, setMainCostRank] = useState<CoinRankItem[]>([]);

  // Signals data
  const [opportunitySignals, setOpportunitySignals] = useState<SignalItem[]>([]);
  const [riskSignals, setRiskSignals] = useState<SignalItem[]>([]);

  // Whale flow data
  const [whaleFlow, setWhaleFlow] = useState<WhaleFlowItem[]>([]);

  // 加载币种映射表
  useEffect(() => {
    valuescanApi.getSymbolMap().then(setSymbolMap).catch(console.error);
  }, []);

  // 当选择币种改变时更新keyword
  const handleSymbolChange = async (newSymbol: string) => {
    setSelectedSymbol(newSymbol);
    const kw = await valuescanApi.getKeywordBySymbol(newSymbol);
    if (kw) {
      setSelectedKeyword(kw);
    }
  };

  const handleCustomSymbolSearch = async () => {
    if (!customSymbol.trim()) return;
    const kw = symbolMap[customSymbol.toUpperCase()];
    if (kw) {
      setSelectedSymbol(customSymbol.toUpperCase());
      setSelectedKeyword(kw);
      setCustomSymbol('');
    } else {
      setError(`Symbol ${customSymbol} not found`);
    }
  };

  const loadMainForceData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [areas, densePrice, holdCost] = await Promise.all([
        valuescanApi.getDenseAreas(selectedKeyword, 14),
        valuescanApi.getCurrentDenseAreaPrice(selectedKeyword, 14),
        valuescanApi.getCurrentHoldCost(selectedKeyword, 14),
      ]);
      setDenseAreas(areas);
      setCurrentDensePrice(densePrice);
      setCurrentHoldCost(holdCost);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [selectedKeyword]);

  const loadRankingsData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [g, l, mc] = await Promise.all([
        valuescanApi.getGainers(1, 10),
        valuescanApi.getLosers(1, 10),
        valuescanApi.getMainCostRank(1, 10),
      ]);
      setGainers(g);
      setLosers(l);
      setMainCostRank(mc);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSignalsData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [opp, risk] = await Promise.all([
        valuescanApi.getOpportunitySignals(1, 10),
        valuescanApi.getRiskSignals(1, 10),
      ]);
      setOpportunitySignals(opp);
      setRiskSignals(risk);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadWhaleFlowData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const flow = await valuescanApi.getWhaleFlow(1, 'm5', 1, 10);
      setWhaleFlow(flow);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'mainForce') {
      loadMainForceData();
    } else if (activeTab === 'rankings') {
      loadRankingsData();
    } else if (activeTab === 'signals') {
      loadSignalsData();
    } else if (activeTab === 'whaleFlow') {
      loadWhaleFlowData();
    }
  }, [activeTab, loadMainForceData, loadRankingsData, loadSignalsData, loadWhaleFlowData]);

  const formatPrice = (price: number | string | null) => {
    if (price === null) return '-';
    const num = typeof price === 'string' ? parseFloat(price) : price;
    if (num >= 1000) return `$${num.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
    if (num >= 1) return `$${num.toFixed(2)}`;
    return `$${num.toPrecision(4)}`;
  };

  const formatPercent = (pct: string | number | null) => {
    if (pct === null) return '-';
    const num = typeof pct === 'string' ? parseFloat(pct) : pct;
    const sign = num >= 0 ? '+' : '';
    return `${sign}${num.toFixed(2)}%`;
  };

  const formatTime = (ts: number) => {
    return new Date(ts).toLocaleString();
  };

  const tabs: { key: TabType; label: string }[] = [
    { key: 'mainForce', label: '主力位/成本' },
    { key: 'rankings', label: '排行榜' },
    { key: 'signals', label: '信号' },
    { key: 'whaleFlow', label: '资金流' },
  ];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          ValuScan 数据面板
        </h3>
        
        {/* 币种选择器 */}
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {COMMON_COINS.slice(0, 5).map((coin) => (
              <button
                key={coin}
                onClick={() => handleSymbolChange(coin)}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  selectedSymbol === coin
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                {coin}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1">
            <input
              type="text"
              value={customSymbol}
              onChange={(e) => setCustomSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && handleCustomSymbolSearch()}
              placeholder="其他币种"
              className="w-20 px-2 py-1 text-xs border rounded dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            />
            <button
              onClick={handleCustomSymbolSearch}
              className="px-2 py-1 text-xs bg-gray-200 dark:bg-gray-600 rounded hover:bg-gray-300 dark:hover:bg-gray-500"
            >
              查询
            </button>
          </div>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            当前: <span className="font-medium text-blue-600 dark:text-blue-400">{selectedSymbol}</span>
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 mb-4">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'text-blue-600 border-b-2 border-blue-600 dark:text-blue-400'
                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Loading & Error */}
      {loading && (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3 mb-4">
          <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Main Force Tab */}
      {!loading && activeTab === 'mainForce' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">当前主力位 (绿色线)</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                {formatPrice(currentDensePrice)}
              </p>
            </div>
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">当前主力成本</p>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {formatPrice(currentHoldCost)}
              </p>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              主力位历史 ({selectedSymbol}) - 最近 {Math.min(denseAreas.length, 10)} 条
            </h4>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 dark:text-gray-400">
                    <th className="py-2 px-3">时间</th>
                    <th className="py-2 px-3">价格</th>
                  </tr>
                </thead>
                <tbody>
                  {denseAreas.slice(-10).reverse().map((point, idx) => (
                    <tr key={idx} className="border-t border-gray-100 dark:border-gray-700">
                      <td className="py-2 px-3 text-gray-600 dark:text-gray-300">
                        {formatTime(point.time)}
                      </td>
                      <td className="py-2 px-3 font-mono text-green-600 dark:text-green-400">
                        {formatPrice(point.price)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Rankings Tab */}
      {!loading && activeTab === 'rankings' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Gainers */}
          <div>
            <h4 className="text-sm font-medium text-green-600 dark:text-green-400 mb-2">涨幅榜</h4>
            <div className="space-y-1">
              {gainers.slice(0, 5).map((coin, idx) => (
                <div
                  key={idx}
                  className="flex justify-between items-center py-1 text-sm"
                >
                  <span className="text-gray-700 dark:text-gray-300">{coin.symbol}</span>
                  <span className="text-green-600 dark:text-green-400">
                    {formatPercent(coin.percentChange24h)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Losers */}
          <div>
            <h4 className="text-sm font-medium text-red-600 dark:text-red-400 mb-2">跌幅榜</h4>
            <div className="space-y-1">
              {losers.slice(0, 5).map((coin, idx) => (
                <div
                  key={idx}
                  className="flex justify-between items-center py-1 text-sm"
                >
                  <span className="text-gray-700 dark:text-gray-300">{coin.symbol}</span>
                  <span className="text-red-600 dark:text-red-400">
                    {formatPercent(coin.percentChange24h)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Main Cost Rank */}
          <div>
            <h4 className="text-sm font-medium text-blue-600 dark:text-blue-400 mb-2">主力成本偏离</h4>
            <div className="space-y-1">
              {mainCostRank.slice(0, 5).map((coin, idx) => (
                <div
                  key={idx}
                  className="flex justify-between items-center py-1 text-sm"
                >
                  <span className="text-gray-700 dark:text-gray-300">{coin.symbol}</span>
                  <span className={`${
                    parseFloat(coin.deviation || '0') < 0
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-green-600 dark:text-green-400'
                  }`}>
                    {formatPercent(coin.deviation || '0')}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Signals Tab */}
      {!loading && activeTab === 'signals' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Opportunity Signals */}
          <div>
            <h4 className="text-sm font-medium text-green-600 dark:text-green-400 mb-2">
              机会看涨信号
            </h4>
            <div className="space-y-1">
              {opportunitySignals.slice(0, 5).map((signal, idx) => (
                <div
                  key={idx}
                  className="flex justify-between items-center py-1 text-sm"
                >
                  <span className="text-gray-700 dark:text-gray-300">{signal.symbol}</span>
                  <span className="text-green-600 dark:text-green-400">
                    评分: {signal.score || '-'}
                  </span>
                </div>
              ))}
              {opportunitySignals.length === 0 && (
                <p className="text-gray-500 text-sm">暂无信号</p>
              )}
            </div>
          </div>

          {/* Risk Signals */}
          <div>
            <h4 className="text-sm font-medium text-red-600 dark:text-red-400 mb-2">
              风险看跌信号
            </h4>
            <div className="space-y-1">
              {riskSignals.slice(0, 5).map((signal, idx) => (
                <div
                  key={idx}
                  className="flex justify-between items-center py-1 text-sm"
                >
                  <span className="text-gray-700 dark:text-gray-300">{signal.symbol}</span>
                  <span className="text-red-600 dark:text-red-400">
                    评分: {signal.score || '-'} 等级: {signal.grade || '-'}
                  </span>
                </div>
              ))}
              {riskSignals.length === 0 && (
                <p className="text-gray-500 text-sm">暂无信号</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Whale Flow Tab */}
      {!loading && activeTab === 'whaleFlow' && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            主力资金流 (5分钟)
          </h4>
          <div className="space-y-2">
            {whaleFlow.slice(0, 10).map((flow, idx) => (
              <div
                key={idx}
                className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-700"
              >
                <span className="text-gray-700 dark:text-gray-300 font-medium">
                  {flow.symbol}
                </span>
                <span
                  className={`font-mono ${
                    flow.tradeInflow >= 0
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {flow.tradeInflow >= 0 ? '+' : ''}
                  ${Math.abs(flow.tradeInflow).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
              </div>
            ))}
            {whaleFlow.length === 0 && (
              <p className="text-gray-500 text-sm">暂无数据</p>
            )}
          </div>
        </div>
      )}

      {/* Refresh Button */}
      <div className="mt-4 flex justify-end">
        <button
          onClick={() => {
            if (activeTab === 'mainForce') loadMainForceData();
            else if (activeTab === 'rankings') loadRankingsData();
            else if (activeTab === 'signals') loadSignalsData();
            else if (activeTab === 'whaleFlow') loadWhaleFlowData();
          }}
          disabled={loading}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          刷新数据
        </button>
      </div>
    </div>
  );
};

export default ValuScanDataPanel;
