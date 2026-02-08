import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, Input } from '../../components/ui';
import { cn } from '../../utils/cn';
import { toApiError } from '../../services/api';
import {
  buildGraph,
  generateOntology,
  getGraphData,
  getProject,
  getTaskStatus,
  GraphData,
  GraphProject,
  GraphTask,
} from '../../services/mirofishGraphApi';
import LogicGraphPanel from './LogicGraphPanel';

type MarketLogicLabProps = {
  symbol: string;
  summary: Record<string, unknown> | null;
};

type PhaseStatus = 'idle' | 'active' | 'completed' | 'error';

type PhaseState = {
  status: PhaseStatus;
  label: string;
};

const asRecord = (value: unknown): Record<string, unknown> | null => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
};

const asArray = (value: unknown): Array<Record<string, unknown>> => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item) => item && typeof item === 'object') as Array<Record<string, unknown>>;
};

const getString = (value: unknown, fallback = 'n/a') => {
  if (typeof value === 'string' && value.trim()) {
    return value.trim();
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value.toString();
  }
  return fallback;
};

const getNumber = (value: unknown) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const formatNumber = (value: unknown, digits = 2) => {
  const numeric = getNumber(value);
  if (numeric === null) {
    return 'n/a';
  }
  return numeric.toFixed(digits);
};

const buildDefaultFocus = (symbol: string) =>
  `Map the key drivers for ${symbol} across macro, flows, sentiment, technical structure, and cross-asset links.`;

export const MarketLogicLab = ({ symbol, summary }: MarketLogicLabProps) => {
  const summaryRecord = summary ?? null;
  const summaryData = asRecord(summaryRecord?.data);
  const marketSnapshot = asRecord(summaryData?.market_snapshot);
  const marketSources = asArray(summaryData?.market_sources);
  const aiForecast = asRecord(summaryRecord?.ai_forecast);
  const advice = asRecord(summaryRecord?.advice);

  const resolvedSymbol = getString(summaryRecord?.resolved_symbol || summaryRecord?.symbol, symbol || 'Asset');

  const [analysisFocus, setAnalysisFocus] = useState(() => buildDefaultFocus(symbol));
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [project, setProject] = useState<GraphProject | null>(null);
  const [taskStatus, setTaskStatus] = useState<GraphTask | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [graphId, setGraphId] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [manualGraphId, setManualGraphId] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState<string | null>(null);

  useEffect(() => {
    setAnalysisFocus(buildDefaultFocus(symbol));
  }, [symbol]);

  const contextLines = useMemo(() => {
    const lines: string[] = [];
    lines.push(`Asset: ${resolvedSymbol}`);
    lines.push(`Focus: ${analysisFocus}`);
    lines.push(`Direction: ${getString(summaryRecord?.direction)}`);
    lines.push(`Confidence: ${getString(summaryRecord?.confidence)}`);
    lines.push(`Score: ${getString(summaryRecord?.score)}`);
    if (marketSnapshot) {
      lines.push(`Price: ${formatNumber(marketSnapshot.price, 2)}`);
      lines.push(`24h High: ${formatNumber(marketSnapshot.high_24h, 2)}`);
      lines.push(`24h Low: ${formatNumber(marketSnapshot.low_24h, 2)}`);
      lines.push(`24h Change: ${formatNumber(marketSnapshot.price_change_percent, 2)}%`);
    }
    if (aiForecast) {
      lines.push(`AI Summary: ${getString(aiForecast.summary)}`);
      const keyFactors = Array.isArray(aiForecast.key_factors) ? aiForecast.key_factors.slice(0, 5) : [];
      if (keyFactors.length > 0) {
        lines.push(`Key Factors: ${keyFactors.map((item) => String(item)).join(', ')}`);
      }
    }
    if (advice) {
      lines.push(`Action: ${getString(advice.action)}`);
      lines.push(`Risk: ${getString(advice.risk_level)}`);
      lines.push(`Valid Until: ${getString(advice.effective_until)}`);
    }
    if (marketSources.length > 0) {
      const formatted = marketSources
        .slice(0, 5)
        .map((source) => {
          const name = getString(source.name, 'source');
          const weight = getNumber(source.weight);
          return `${name}${weight !== null ? ` (${Math.round(weight * 100)}%)` : ''}`;
        });
      lines.push(`Data Sources: ${formatted.join(', ')}`);
    }
    lines.push('Model: valuescan');
    return lines;
  }, [analysisFocus, marketSnapshot, marketSources, aiForecast, advice, summaryRecord, resolvedSymbol]);

  const contextPreview = useMemo(() => contextLines.join('\n'), [contextLines]);

  const overallStatus = useMemo(() => {
    if (graphError) {
      return { label: 'Error', color: 'bg-red-500' };
    }
    if (isGenerating || taskStatus?.status === 'processing' || taskStatus?.status === 'pending') {
      return { label: 'Processing', color: 'bg-neutral-200' };
    }
    if (graphData) {
      return { label: 'Ready', color: 'bg-neutral-400' };
    }
    return { label: 'Idle', color: 'bg-neutral-600' };
  }, [graphData, graphError, isGenerating, taskStatus?.status]);

  const buildPayload = () => {
    const lines = [`GeneratedAt: ${new Date().toISOString()}`, ...contextLines];
    return lines.join('\n');
  };

  const fetchGraph = async (nextGraphId: string) => {
    if (!nextGraphId) {
      return;
    }
    setGraphLoading(true);
    setGraphError(null);
    try {
      const response = await getGraphData(nextGraphId);
      if (!response.success || !response.data) {
        setGraphError(response.error || 'Unable to load graph data.');
        setGraphData(null);
        return;
      }
      setGraphData(response.data);
    } catch (error) {
      const apiError = toApiError(error);
      setGraphError(apiError.message || 'Unable to load graph data.');
      setGraphData(null);
    } finally {
      setGraphLoading(false);
    }
  };

  const refreshProject = async (nextProjectId: string) => {
    try {
      const response = await getProject(nextProjectId);
      if (response.success && response.data) {
        setProject(response.data);
      }
    } catch (error) {
      const apiError = toApiError(error);
      setGraphError(apiError.message || 'Unable to refresh project data.');
    }
  };
  const handleBuildGraph = async () => {
    if (isGenerating) {
      return;
    }
    if (!summaryRecord) {
      setGraphError('Run a forecast before building the logic graph.');
      return;
    }
    setGraphError(null);
    setGraphData(null);
    setTaskStatus(null);
    setTaskId(null);
    setGraphId(null);
    setProject(null);
    setProjectId(null);

    try {
      setIsGenerating(true);
      const payloadText = buildPayload();
      const file = new File([payloadText], `${resolvedSymbol}-context.txt`, { type: 'text/plain' });
      const formData = new FormData();
      formData.append('files', file);
      formData.append('simulation_requirement', analysisFocus.trim() || buildDefaultFocus(symbol));
      formData.append('project_name', `${resolvedSymbol} Market Context`);
      formData.append('additional_context', 'Forecast context assembled from ValueScan data.');

      const response = await generateOntology(formData);
      if (!response.success || !response.data) {
        setGraphError(response.error || 'Ontology generation failed.');
        return;
      }
      setProject(response.data);
      setProjectId(response.data.project_id);

      const buildResponse = await buildGraph(response.data.project_id, `${resolvedSymbol} Logic Graph`);
      if (!buildResponse.success || !buildResponse.data?.task_id) {
        setGraphError(buildResponse.error || 'Graph build could not be started.');
        return;
      }

      setTaskId(buildResponse.data.task_id);
      setTaskStatus({ task_id: buildResponse.data.task_id, status: 'pending' });
    } catch (error) {
      const apiError = toApiError(error);
      setGraphError(apiError.message || 'Graph build failed.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleLoadGraph = async () => {
    if (!manualGraphId.trim()) {
      setGraphError('Provide a graph id to load.');
      return;
    }
    const id = manualGraphId.trim();
    setGraphId(id);
    await fetchGraph(id);
  };

  useEffect(() => {
    if (!taskId) {
      return undefined;
    }

    let isActive = true;
    let interval: ReturnType<typeof setInterval> | null = null;
    const stopPolling = () => {
      if (!isActive) {
        return;
      }
      isActive = false;
      if (interval) {
        clearInterval(interval);
      }
    };

    const poll = async () => {
      if (!isActive) {
        return;
      }
      try {
        const response = await getTaskStatus(taskId);
        if (!response.success || !response.data) {
          if (isActive) {
            setGraphError(response.error || 'Unable to retrieve build status.');
          }
          return;
        }
        if (!isActive) {
          return;
        }
        setTaskStatus(response.data);

        if (response.data.status === 'completed') {
          const nextGraphId = getString(response.data.result?.graph_id, '');
          if (nextGraphId) {
            setGraphId(nextGraphId);
            await fetchGraph(nextGraphId);
          }
          if (projectId) {
            await refreshProject(projectId);
          }
          stopPolling();
        }

        if (response.data.status === 'failed') {
          setGraphError(response.data.error || response.data.message || 'Graph build failed.');
          stopPolling();
        }
      } catch (error) {
        if (!isActive) {
          return;
        }
        const apiError = toApiError(error);
        setGraphError(apiError.message || 'Graph build failed.');
      }
    };

    interval = setInterval(() => {
      void poll();
    }, 4000);
    void poll();

    return () => {
      stopPolling();
    };
  }, [projectId, taskId]);

  const currentPhase = graphData ? 2 : project?.ontology ? 1 : 0;
  const isSimulating = taskStatus?.status === 'processing' || taskStatus?.status === 'pending';

  const resolvePhaseState = (phase: number): PhaseState => {
    if (phase === 0) {
      if (graphError) {
        return { status: 'error', label: 'error' };
      }
      if (isGenerating) {
        return { status: 'active', label: 'running' };
      }
      if (project?.ontology) {
        return { status: 'completed', label: 'complete' };
      }
      return { status: 'idle', label: 'waiting' };
    }

    if (phase === 1) {
      if (graphError) {
        return { status: 'error', label: 'error' };
      }
      if (isSimulating) {
        return { status: 'active', label: 'building' };
      }
      if (graphData) {
        return { status: 'completed', label: 'complete' };
      }
      return { status: 'idle', label: project?.ontology ? 'queued' : 'waiting' };
    }

    if (graphData) {
      return { status: 'completed', label: 'ready' };
    }

    return { status: 'idle', label: 'pending' };
  };

  const statusClass = (status: PhaseStatus) => {
    switch (status) {
      case 'active':
        return 'bg-neutral-100 text-neutral-900';
      case 'completed':
        return 'bg-neutral-300 text-neutral-900';
      case 'error':
        return 'bg-red-500 text-white';
      default:
        return 'bg-neutral-800 text-neutral-400';
    }
  };

  const phaseZero = resolvePhaseState(0);
  const phaseOne = resolvePhaseState(1);
  const phaseTwo = resolvePhaseState(2);

  const graphStats = {
    nodes: graphData?.node_count ?? graphData?.nodes?.length ?? 0,
    edges: graphData?.edge_count ?? graphData?.edges?.length ?? 0,
  };
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <LogicGraphPanel
        graphData={graphData}
        loading={graphLoading}
        currentPhase={currentPhase}
        isSimulating={isSimulating}
        onRefresh={() => {
          if (graphId) {
            void fetchGraph(graphId);
          }
        }}
      />

      <div className="flex flex-col gap-6">
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader className="border-neutral-800">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs uppercase tracking-[0.3em] text-neutral-500">Logic Analysis Path</p>
                <h3 className="text-lg font-semibold text-white">Graph Intelligence Pipeline</h3>
              </div>
              <div className="flex items-center gap-2 text-xs text-neutral-400">
                <span className={cn('h-2 w-2 rounded-full', overallStatus.color)} />
                <span>{overallStatus.label}</span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="rounded-xl border border-neutral-800 bg-neutral-950/60 p-4">
              <p className="text-[10px] uppercase tracking-[0.3em] text-neutral-500">Focus Prompt</p>
              <textarea
                value={analysisFocus}
                onChange={(event) => setAnalysisFocus(event.target.value)}
                rows={4}
                className="mt-2 w-full resize-none rounded-lg border border-neutral-800 bg-neutral-950/80 px-3 py-2 text-xs text-neutral-100 placeholder:text-neutral-600 focus:border-neutral-500 focus:outline-none"
              />
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={() => void handleBuildGraph()}
                  disabled={isGenerating}
                  className="rounded-full border border-neutral-200 bg-neutral-100 px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-neutral-900 transition hover:bg-white disabled:cursor-not-allowed"
                >
                  {isGenerating ? 'Building...' : 'Generate Logic Graph'}
                </button>
                <span className="text-[10px] uppercase tracking-[0.25em] text-neutral-500">
                  Auto-seeded from forecast
                </span>
              </div>
            </div>

            <div className="rounded-xl border border-neutral-800 bg-neutral-950/60 p-4">
              <p className="text-[10px] uppercase tracking-[0.3em] text-neutral-500">Context Snapshot</p>
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs text-neutral-300">
                {contextPreview}
              </pre>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-xl border border-neutral-800 bg-neutral-950/50 px-4 py-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-neutral-500">Step 01</p>
                  <p className="text-sm font-semibold text-white">Ontology Extraction</p>
                  <p className="text-xs text-neutral-500">/api/mirofish/graph/ontology/generate</p>
                </div>
                <span className={cn('rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.25em]', statusClass(phaseZero.status))}>
                  {phaseZero.label}
                </span>
              </div>
              {project?.analysis_summary && (
                <div className="rounded-xl border border-neutral-800 bg-neutral-950/70 p-3 text-xs text-neutral-300">
                  {project.analysis_summary}
                </div>
              )}
              {project?.ontology?.entity_types && project.ontology.entity_types.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {project.ontology.entity_types.map((entity) => (
                    <span
                      key={entity.name}
                      className="rounded-full border border-neutral-800 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-neutral-400"
                    >
                      {entity.name}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-xl border border-neutral-800 bg-neutral-950/50 px-4 py-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-neutral-500">Step 02</p>
                  <p className="text-sm font-semibold text-white">Graph Build</p>
                  <p className="text-xs text-neutral-500">/api/mirofish/graph/build</p>
                </div>
                <span className={cn('rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.25em]', statusClass(phaseOne.status))}>
                  {phaseOne.label}
                </span>
              </div>
              {taskStatus && (
                <div className="rounded-xl border border-neutral-800 bg-neutral-950/70 p-3 text-xs text-neutral-300">
                  <div className="flex items-center justify-between">
                    <span>{taskStatus.message || 'Graph build running'}</span>
                    <span className="text-neutral-400">{taskStatus.progress ?? 0}%</span>
                  </div>
                  <div className="mt-2 h-2 w-full rounded-full bg-neutral-800">
                    <div
                      className="h-2 rounded-full bg-neutral-200"
                      style={{ width: `${Math.min(taskStatus.progress ?? 0, 100)}%` }}
                    />
                  </div>
                </div>
              )}
              <div className="grid gap-2 rounded-xl border border-neutral-800 bg-neutral-950/70 p-3 text-xs text-neutral-400">
                <div className="flex items-center justify-between">
                  <span>Nodes</span>
                  <span className="text-neutral-200">{graphStats.nodes}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Edges</span>
                  <span className="text-neutral-200">{graphStats.edges}</span>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-xl border border-neutral-800 bg-neutral-950/50 px-4 py-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-neutral-500">Step 03</p>
                  <p className="text-sm font-semibold text-white">Decision Window</p>
                  <p className="text-xs text-neutral-500">Logic graph ready for reasoning</p>
                </div>
                <span className={cn('rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.25em]', statusClass(phaseTwo.status))}>
                  {phaseTwo.label}
                </span>
              </div>
            </div>

            {graphError && (
              <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-xs text-red-300">
                {graphError}
              </div>
            )}

            <div className="rounded-xl border border-neutral-800 bg-neutral-950/60 p-4">
              <p className="text-[10px] uppercase tracking-[0.3em] text-neutral-500">Load Existing Graph</p>
              <div className="mt-3 flex flex-col gap-2">
                <Input
                  value={manualGraphId}
                  onChange={(event) => setManualGraphId(event.target.value)}
                  placeholder="Graph id"
                  className="border-neutral-800 bg-neutral-950/70 text-neutral-100 placeholder:text-neutral-600"
                />
                <button
                  type="button"
                  onClick={() => void handleLoadGraph()}
                  className="rounded-full border border-neutral-800 bg-neutral-900/70 px-4 py-2 text-xs uppercase tracking-[0.25em] text-neutral-300 transition hover:border-neutral-500 hover:text-white"
                >
                  Load Graph
                </button>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader className="border-neutral-800">
            <p className="text-xs uppercase tracking-[0.3em] text-neutral-500">Project Info</p>
          </CardHeader>
          <CardContent className="space-y-3 text-xs text-neutral-400">
            <div className="flex items-center justify-between">
              <span>Project</span>
              <span className="text-neutral-200">{project?.name || 'n/a'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Project ID</span>
              <span className="font-mono text-[10px] text-neutral-500">{project?.project_id || 'n/a'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Graph ID</span>
              <span className="font-mono text-[10px] text-neutral-500">{graphId || project?.graph_id || 'n/a'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Status</span>
              <span className="text-neutral-200">{project?.status || taskStatus?.status || 'idle'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Last Updated</span>
              <span className="text-neutral-300">{project?.updated_at || 'n/a'}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default MarketLogicLab;
