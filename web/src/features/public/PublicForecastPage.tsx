import { useMemo, useState } from 'react';
import { Button, Card, CardContent, CardHeader, Input } from '../../components/ui';
import { fetchForecast } from '../../services/forecastApi';
import { toApiError } from '../../services/api';
import { NetworkMesh } from '../../components/visuals/NetworkMesh';
import { MarketLogicLab } from './MarketLogicLab';

const quickSymbols = [
  { label: 'BTC', value: 'BTC' },
  { label: 'ETH', value: 'ETH' },
  { label: 'Gold', value: 'GC=F' },
  { label: 'Silver', value: 'SI=F' },
  { label: 'Nasdaq 100', value: '^IXIC' },
  { label: 'S&P 500', value: '^GSPC' },
  { label: 'Crude Oil', value: 'CL=F' },
  { label: 'Brent', value: 'BZ=F' },
];

const normalizeNumber = (value: unknown) => {
  if (typeof value === 'number') {
    return value;
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const formatNumber = (value: unknown, digits = 2) => {
  const normalized = normalizeNumber(value);
  if (normalized === null) {
    return 'n/a';
  }
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(normalized);
};

const formatPercent = (value: unknown) => {
  const normalized = normalizeNumber(value);
  if (normalized === null) {
    return 'n/a';
  }
  return `${formatNumber(normalized, 2)}%`;
};

export const PublicForecastPage = () => {
  const [symbol, setSymbol] = useState('BTC');
  const [useLlm, setUseLlm] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleForecast = async (nextSymbol?: string) => {
    const resolvedSymbol = (nextSymbol ?? symbol).trim();
    if (!resolvedSymbol) {
      setError('Please enter a symbol.');
      return;
    }
    if (loading) {
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetchForecast(resolvedSymbol, useLlm);
      if (!response?.success) {
        setError(response?.error || 'Forecast failed.');
        setResult(null);
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

  const handleForecastClick = () => {
    void handleForecast();
  };

  const summary = result as Record<string, unknown> | null;
  const aiForecast = summary?.ai_forecast as Record<string, unknown> | undefined;
  const advice = summary?.advice as Record<string, unknown> | undefined;
  const market = (summary?.data as Record<string, unknown> | undefined)?.market_snapshot as
    | Record<string, unknown>
    | undefined;
  const sources = (summary?.data as Record<string, unknown> | undefined)?.market_sources as
    | Array<Record<string, unknown>>
    | undefined;

  const topSources = useMemo(() => {
    if (!Array.isArray(sources)) {
      return [];
    }
    return [...sources]
      .map((source) => ({
        name: String(source.name || 'unknown'),
        weight: typeof source.weight === 'number' ? source.weight : 0,
      }))
      .sort((a, b) => b.weight - a.weight)
      .slice(0, 3);
  }, [sources]);

  return (
    <div className="relative min-h-screen overflow-hidden bg-neutral-950 text-neutral-100 font-['Space_Grotesk']">
      <NetworkMesh className="opacity-60" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.08),_transparent_55%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(255,255,255,0.05),_transparent_60%)]" />
      <div className="relative z-10 flex min-h-screen flex-col">
        <header className="flex items-center justify-between px-6 py-6 sm:px-10">
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-[0.3em] text-neutral-500">ValueScan</p>
            <h1 className="text-2xl font-semibold text-white sm:text-3xl">Market Direction Lab</h1>
          </div>
          <a
            href="/admin"
            className="rounded-full border border-neutral-800 bg-neutral-900/60 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-neutral-300 transition hover:border-neutral-500 hover:text-white"
          >
            Admin
          </a>
        </header>

        <main className="flex flex-1 flex-col gap-8 px-6 pb-12 sm:px-10">
          <div className="flex flex-1 flex-col gap-8 lg:flex-row">
            <section className="flex w-full flex-col gap-6 lg:w-[55%]">
            <Card className="border-neutral-800 bg-neutral-900/70">
              <CardHeader className="border-neutral-800">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-white">Predict Any Asset</h2>
                    <p className="text-sm text-neutral-400">
                      Crypto, stocks, indices, metals, and futures. Enter a symbol to see the next 24h bias.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-neutral-400">
                    <span>AI Forecast</span>
                    <button
                      type="button"
                      onClick={() => setUseLlm((prev) => !prev)}
                      className={`rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.2em] transition ${
                        useLlm
                          ? 'border-neutral-100 bg-neutral-100 text-neutral-900'
                          : 'border-neutral-700 bg-neutral-900 text-neutral-400'
                      }`}
                    >
                      {useLlm ? 'On' : 'Off'}
                    </button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Input
                    value={symbol}
                    onChange={(event) => setSymbol(event.target.value)}
                    placeholder="BTC / AAPL / GC=F / XAUUSD"
                    className="border-neutral-800 bg-neutral-950/60 text-neutral-100 placeholder:text-neutral-500 focus:border-neutral-500 focus:ring-neutral-500/30"
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        void handleForecast();
                      }
                    }}
                  />
                  <Button
                    onClick={handleForecastClick}
                    disabled={loading}
                    className="border border-neutral-200 bg-neutral-100 text-neutral-900 hover:bg-white focus:ring-neutral-300"
                  >
                    {loading ? 'Running...' : 'Run Forecast'}
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {quickSymbols.map((item) => (
                    <button
                      key={item.value}
                      type="button"
                      onClick={() => {
                        setSymbol(item.value);
                        void handleForecast(item.value);
                      }}
                      className="rounded-full border border-neutral-800 bg-neutral-950/60 px-3 py-1 text-xs text-neutral-300 transition hover:border-neutral-500 hover:text-white"
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
                {error && <div className="text-sm text-red-400">{error}</div>}
              </CardContent>
            </Card>

            <Card className="border-neutral-800 bg-neutral-900/70">
              <CardHeader className="border-neutral-800">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-white">Live Snapshot</h3>
                  <span className="text-xs text-neutral-500">
                    {summary?.as_of ? `As of ${String(summary.as_of)}` : 'Awaiting data'}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2 rounded-lg border border-neutral-800 bg-neutral-950/50 p-4">
                  <p className="text-xs uppercase tracking-widest text-neutral-500">Price</p>
                  <p className="text-2xl font-semibold text-white">{formatNumber(market?.price, 2)}</p>
                  <p className="text-xs text-neutral-400">Change: {formatPercent(market?.price_change_percent)}</p>
                </div>
                <div className="space-y-2 rounded-lg border border-neutral-800 bg-neutral-950/50 p-4">
                  <p className="text-xs uppercase tracking-widest text-neutral-500">Range</p>
                  <p className="text-sm text-neutral-200">High: {formatNumber(market?.high_24h, 2)}</p>
                  <p className="text-sm text-neutral-200">Low: {formatNumber(market?.low_24h, 2)}</p>
                  <p className="text-xs text-neutral-500">Volume: {formatNumber(market?.volume_24h, 0)}</p>
                </div>
                <div className="space-y-2 rounded-lg border border-neutral-800 bg-neutral-950/50 p-4 sm:col-span-2">
                  <p className="text-xs uppercase tracking-widest text-neutral-500">Data Priority</p>
                  <div className="flex flex-wrap gap-2">
                    {topSources.length > 0 ? (
                      topSources.map((source) => (
                        <span
                          key={source.name}
                          className="rounded-full border border-neutral-800 px-3 py-1 text-xs text-neutral-300"
                        >
                          {source.name} {source.weight ? `(${Math.round(source.weight * 100)}%)` : ''}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-neutral-500">Awaiting source weights</span>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            </section>

            <section className="flex w-full flex-col gap-6 lg:w-[45%]">
            <Card className="border-neutral-800 bg-neutral-900/70">
              <CardHeader className="border-neutral-800">
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-[0.3em] text-neutral-500">Forecast</p>
                  <h2 className="text-xl font-semibold text-white">
                    {String(summary?.resolved_symbol || summary?.symbol || symbol)}
                  </h2>
                  <p className="text-xs text-neutral-400">
                    {summary?.asset_class ? String(summary.asset_class) : 'multi-asset'} - Next 24h
                  </p>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-lg border border-neutral-800 bg-neutral-950/50 p-3">
                    <p className="text-xs uppercase tracking-widest text-neutral-500">Bias</p>
                    <p className="text-lg font-semibold text-white">{String(summary?.direction ?? 'n/a')}</p>
                  </div>
                  <div className="rounded-lg border border-neutral-800 bg-neutral-950/50 p-3">
                    <p className="text-xs uppercase tracking-widest text-neutral-500">Confidence</p>
                    <p className="text-lg font-semibold text-white">{String(summary?.confidence ?? 'n/a')}</p>
                  </div>
                  <div className="rounded-lg border border-neutral-800 bg-neutral-950/50 p-3">
                    <p className="text-xs uppercase tracking-widest text-neutral-500">Score</p>
                    <p className="text-lg font-semibold text-white">{String(summary?.score ?? 'n/a')}</p>
                  </div>
                </div>

                {aiForecast && (
                  <div className="rounded-lg border border-neutral-800 bg-neutral-950/60 p-4">
                    <p className="text-xs uppercase tracking-widest text-neutral-500">AI Summary</p>
                    <p className="mt-2 text-sm text-neutral-200">{String(aiForecast.summary || 'n/a')}</p>
                    {Array.isArray(aiForecast.key_factors) && aiForecast.key_factors.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {aiForecast.key_factors.slice(0, 4).map((item) => (
                          <span
                            key={String(item)}
                            className="rounded-full border border-neutral-800 px-3 py-1 text-xs text-neutral-300"
                          >
                            {String(item)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {advice && (
                  <div className="rounded-lg border border-neutral-700 bg-neutral-900/80 p-4">
                    <p className="text-xs uppercase tracking-widest text-neutral-400">Investment Guidance</p>
                    <div className="mt-3 grid gap-3 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-neutral-400">Action</span>
                        <span className="font-semibold text-white">{String(advice.action || 'wait')}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-neutral-400">Risk</span>
                        <span className="font-semibold text-white">{String(advice.risk_level || 'high')}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-neutral-400">Valid Until</span>
                        <span className="font-semibold text-white">{String(advice.effective_until || 'n/a')}</span>
                      </div>
                      {Array.isArray(advice.rationale) && advice.rationale.length > 0 && (
                        <div className="rounded-lg border border-neutral-800 bg-neutral-950/50 p-3 text-xs text-neutral-300">
                          {advice.rationale.slice(0, 3).map((item, index) => (
                            <div key={`${index}-${item}`}>- {String(item)}</div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {!summary && (
                  <div className="rounded-lg border border-dashed border-neutral-800 p-6 text-center text-sm text-neutral-500">
                    Choose a symbol to generate a forecast and advisory window.
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-neutral-800 bg-neutral-900/70">
              <CardHeader className="border-neutral-800">
                <h3 className="text-sm uppercase tracking-[0.3em] text-neutral-500">Operating Window</h3>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-neutral-400">
                <p>Predictions are optimized for a 24 hour horizon unless otherwise stated.</p>
                <p>Combine with your own risk controls and position sizing.</p>
                <p className="text-xs text-neutral-500">Model: valuescan</p>
              </CardContent>
            </Card>
            </section>
          </div>

          <section className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-neutral-500">MiroFish Logic</p>
                <h2 className="text-xl font-semibold text-white">Market Intelligence Graph</h2>
              </div>
              <span className="text-xs text-neutral-500">Embedded analysis path + logic node graph</span>
            </div>
            <MarketLogicLab symbol={symbol} summary={summary} />
          </section>
        </main>
      </div>
    </div>
  );
};

export default PublicForecastPage;

