import { useState } from 'react';
import { Card, CardContent, CardHeader, CardFooter, Input, Button, Switch } from '../../components/ui';
import { fetchForecast } from '../../services/forecastApi';
import { toApiError } from '../../services/api';

export const ForecastPage = () => {
  const [symbol, setSymbol] = useState('BTC');
  const [useLlm, setUseLlm] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleForecast = async () => {
    if (!symbol.trim()) {
      setError('Symbol is required.');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetchForecast(symbol.trim(), useLlm);
      if (!response?.success) {
        setError(response?.error || 'Forecast failed.');
        return;
      }
      setResult(response.data || null);
    } catch (err) {
      const apiError = toApiError(err);
      setError(apiError.message || 'Forecast failed.');
    } finally {
      setLoading(false);
    }
  };

  const summary = result as Record<string, unknown> | null;
  const aiForecast = summary?.ai_forecast as Record<string, unknown> | undefined;
  const advice = summary?.advice as Record<string, unknown> | undefined;

  return (
    <div className="p-6 space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Forecast</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Enter a trading pair or ticker (BTC, ETH, AAPL, GC=F, XAUUSD).
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600 dark:text-gray-300">Use AI</span>
              <Switch checked={useLlm} onChange={setUseLlm} />
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 md:flex-row">
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="BTC / AAPL / GC=F / XAGUSD"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleForecast();
                }
              }}
            />
            <Button onClick={handleForecast} disabled={loading}>
              {loading ? 'Forecasting...' : 'Run Forecast'}
            </Button>
          </div>
          {error && (
            <div className="text-sm text-red-600 dark:text-red-400">{error}</div>
          )}
        </CardContent>
      </Card>

      {summary && (
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {String(summary.resolved_symbol || summary.symbol || symbol)}
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {String(summary.asset_class || 'market')} - {String(summary.as_of || '')}
                </p>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-gray-500 dark:text-gray-400">
                  Direction: <span className="text-gray-900 dark:text-gray-100">{String(summary.direction)}</span>
                </span>
                <span className="text-gray-500 dark:text-gray-400">
                  Confidence: <span className="text-gray-900 dark:text-gray-100">{String(summary.confidence)}</span>
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {aiForecast && (
              <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-4">
                <div className="text-sm text-gray-500 dark:text-gray-400">AI Forecast</div>
                <div className="mt-1 text-base text-gray-900 dark:text-gray-100">
                  {String(aiForecast.summary || 'No summary')}
                </div>
              </div>
            )}
            {advice && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-100">
                <div className="text-sm uppercase tracking-wide text-amber-600 dark:text-amber-300">Investment Guidance</div>
                <div className="mt-2 grid gap-2 text-sm md:grid-cols-2">
                  <div>
                    <div className="text-xs text-amber-600 dark:text-amber-300">Action</div>
                    <div className="font-semibold">{String(advice.action || 'wait')}</div>
                  </div>
                  <div>
                    <div className="text-xs text-amber-600 dark:text-amber-300">Risk</div>
                    <div className="font-semibold">{String(advice.risk_level || 'high')}</div>
                  </div>
                  <div>
                    <div className="text-xs text-amber-600 dark:text-amber-300">Bias</div>
                    <div className="font-semibold">{String(advice.bias || 'sideways')}</div>
                  </div>
                  <div>
                    <div className="text-xs text-amber-600 dark:text-amber-300">Horizon</div>
                    <div className="font-semibold">{String(advice.time_horizon_hours || 24)}h</div>
                  </div>
                  <div className="md:col-span-2">
                    <div className="text-xs text-amber-600 dark:text-amber-300">Valid Until</div>
                    <div className="font-semibold">{String(advice.effective_until || 'n/a')}</div>
                  </div>
                </div>
                {Array.isArray(advice.rationale) && advice.rationale.length > 0 && (
                  <div className="mt-3 text-xs text-amber-700 dark:text-amber-200">
                    {advice.rationale.slice(0, 3).map((item, idx) => (
                      <div key={`${idx}-${item}`}>- {String(item)}</div>
                    ))}
                  </div>
                )}
                {typeof advice.disclaimer === 'string' && advice.disclaimer.trim() !== '' && (
                  <div className="mt-3 text-xs text-amber-700/80 dark:text-amber-200/80">
                    {String(advice.disclaimer)}
                  </div>
                )}
              </div>
            )}
            <pre className="text-xs bg-gray-900 text-gray-100 rounded-lg p-4 overflow-auto">
              {JSON.stringify(summary, null, 2)}
            </pre>
          </CardContent>
          <CardFooter>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Tip: Use GC=F for gold, SI=F for silver, or XAUUSD/XAGUSD aliases.
            </div>
          </CardFooter>
        </Card>
      )}
    </div>
  );
};

export default ForecastPage;
