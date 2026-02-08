import { useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import { cn } from '../../utils/cn';
import type { GraphData, GraphEdge, GraphNode } from '../../services/mirofishGraphApi';

type GraphNodeLayout = d3.SimulationNodeDatum & {
  id: string;
  name: string;
  type: string;
  rawData: GraphNode;
  _dragStartX?: number;
  _dragStartY?: number;
  _isDragging?: boolean;
};

type GraphEdgeLayout = d3.SimulationLinkDatum<GraphNodeLayout> & {
  name: string;
  type: string;
  curvature: number;
  isSelfLoop: boolean;
  pairIndex?: number;
  pairTotal?: number;
  rawData: GraphEdge & {
    source_name?: string;
    target_name?: string;
    isSelfLoopGroup?: boolean;
    selfLoopEdges?: GraphEdge[];
    selfLoopCount?: number;
  };
};

type EntityType = {
  name: string;
  count: number;
  color: string;
};

type SelectedItem =
  | {
      type: 'node';
      data: GraphNode;
      entityType: string;
      color: string;
    }
  | {
      type: 'edge';
      data: GraphEdge & {
        source_name?: string;
        target_name?: string;
        isSelfLoopGroup?: boolean;
        selfLoopEdges?: GraphEdge[];
        selfLoopCount?: number;
      };
    };

type LogicGraphPanelProps = {
  graphData: GraphData | null;
  loading: boolean;
  currentPhase: number;
  isSimulating: boolean;
  onRefresh?: () => void;
};

type ZoomEvent = d3.D3ZoomEvent<SVGSVGElement, unknown>;
type DragEvent = d3.D3DragEvent<SVGCircleElement, GraphNodeLayout, GraphNodeLayout>;

const colorPalette = [
  '#F5F5F5',
  '#D9D9D9',
  '#BFBFBF',
  '#A6A6A6',
  '#8C8C8C',
  '#737373',
  '#5A5A5A',
  '#404040',
];

const formatDateTime = (value?: string) => {
  if (!value) {
    return 'n/a';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
};

export const LogicGraphPanel = ({
  graphData,
  loading,
  currentPhase,
  isSimulating,
  onRefresh,
}: LogicGraphPanelProps) => {
  const graphContainerRef = useRef<HTMLDivElement | null>(null);
  const graphSvgRef = useRef<SVGSVGElement | null>(null);
  const simulationRef = useRef<d3.Simulation<GraphNodeLayout, undefined> | null>(null);
  const linkLabelRef = useRef<d3.Selection<SVGTextElement, GraphEdgeLayout, SVGGElement, unknown> | null>(
    null
  );
  const linkLabelBgRef = useRef<d3.Selection<SVGRectElement, GraphEdgeLayout, SVGGElement, unknown> | null>(
    null
  );
  const [selectedItem, setSelectedItem] = useState<SelectedItem | null>(null);
  const selectedItemRef = useRef<SelectedItem | null>(null);
  const [showEdgeLabels, setShowEdgeLabels] = useState(true);
  const [expandedSelfLoops, setExpandedSelfLoops] = useState<Set<string>>(new Set());
  const [showSimulationFinishedHint, setShowSimulationFinishedHint] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const wasSimulatingRef = useRef(false);

  const entityTypes = useMemo<EntityType[]>(() => {
    const nodes = graphData?.nodes ?? [];
    const typeMap = new Map<string, EntityType>();
    nodes.forEach((node) => {
      const type = node.labels?.find((label) => label !== 'Entity') ?? 'Entity';
      if (!typeMap.has(type)) {
        const colorIndex = typeMap.size % colorPalette.length;
        typeMap.set(type, { name: type, count: 0, color: colorPalette[colorIndex] });
      }
      const entry = typeMap.get(type);
      if (entry) {
        entry.count += 1;
      }
    });
    return Array.from(typeMap.values());
  }, [graphData]);

  useEffect(() => {
    if (wasSimulatingRef.current && !isSimulating) {
      setShowSimulationFinishedHint(true);
    }
    wasSimulatingRef.current = isSimulating;
  }, [isSimulating]);

  useEffect(() => {
    if (linkLabelRef.current) {
      linkLabelRef.current.style('display', showEdgeLabels ? 'block' : 'none');
    }
    if (linkLabelBgRef.current) {
      linkLabelBgRef.current.style('display', showEdgeLabels ? 'block' : 'none');
    }
  }, [showEdgeLabels]);

  useEffect(() => {
    selectedItemRef.current = selectedItem;
  }, [selectedItem]);
  useEffect(() => {
    const container = graphContainerRef.current;
    if (!container || !graphData || !graphSvgRef.current) {
      return undefined;
    }

    const renderGraph = () => {
      const svgElement = graphSvgRef.current;
      const containerEl = graphContainerRef.current;
      if (!svgElement || !containerEl) {
        return;
      }

      const width = containerEl.clientWidth;
      const height = containerEl.clientHeight;
      if (!width || !height) {
        return;
      }

      if (simulationRef.current) {
        simulationRef.current.stop();
      }

      const svg = d3.select(svgElement);
      svg.selectAll('*').remove();

      svg
        .attr('width', width)
        .attr('height', height)
        .attr('viewBox', `0 0 ${width} ${height}`);

      const nodesData = graphData.nodes ?? [];
      const edgesData = graphData.edges ?? [];
      if (nodesData.length === 0) {
        return;
      }

      const nodeMap: Record<string, GraphNode> = {};
      nodesData.forEach((node) => {
        nodeMap[node.uuid] = node;
      });

      const nodes: GraphNodeLayout[] = nodesData.map((node) => ({
        id: node.uuid,
        name: node.name || 'Unnamed',
        type: node.labels?.find((label) => label !== 'Entity') ?? 'Entity',
        rawData: node,
      }));

      const nodeIds = new Set(nodes.map((node) => node.id));
      const tempEdges = edgesData.filter(
        (edge) => nodeIds.has(edge.source_node_uuid) && nodeIds.has(edge.target_node_uuid)
      );

      const edgePairCount: Record<string, number> = {};
      const selfLoopEdges: Record<string, GraphEdge[]> = {};
      tempEdges.forEach((edge) => {
        if (edge.source_node_uuid === edge.target_node_uuid) {
          if (!selfLoopEdges[edge.source_node_uuid]) {
            selfLoopEdges[edge.source_node_uuid] = [];
          }
          selfLoopEdges[edge.source_node_uuid].push({
            ...edge,
            source_name: nodeMap[edge.source_node_uuid]?.name,
            target_name: nodeMap[edge.target_node_uuid]?.name,
          });
          return;
        }
        const pairKey = [edge.source_node_uuid, edge.target_node_uuid].sort().join('_');
        edgePairCount[pairKey] = (edgePairCount[pairKey] || 0) + 1;
      });

      const edgePairIndex: Record<string, number> = {};
      const processedSelfLoops = new Set<string>();
      const edges: GraphEdgeLayout[] = [];

      tempEdges.forEach((edge) => {
        const isSelfLoop = edge.source_node_uuid === edge.target_node_uuid;
        if (isSelfLoop) {
          if (processedSelfLoops.has(edge.source_node_uuid)) {
            return;
          }
          processedSelfLoops.add(edge.source_node_uuid);
          const allSelfLoops = selfLoopEdges[edge.source_node_uuid] ?? [];
          const nodeName = nodeMap[edge.source_node_uuid]?.name || 'Unknown';
          edges.push({
            source: edge.source_node_uuid,
            target: edge.target_node_uuid,
            type: 'SELF_LOOP',
            name: `Self Relations (${allSelfLoops.length})`,
            curvature: 0,
            isSelfLoop: true,
            rawData: {
              ...edge,
              isSelfLoopGroup: true,
              source_name: nodeName,
              target_name: nodeName,
              selfLoopCount: allSelfLoops.length,
              selfLoopEdges: allSelfLoops,
            },
          });
          return;
        }

        const pairKey = [edge.source_node_uuid, edge.target_node_uuid].sort().join('_');
        const totalCount = edgePairCount[pairKey];
        const currentIndex = edgePairIndex[pairKey] || 0;
        edgePairIndex[pairKey] = currentIndex + 1;
        const isReversed = edge.source_node_uuid > edge.target_node_uuid;

        let curvature = 0;
        if (totalCount > 1) {
          const curvatureRange = Math.min(1.2, 0.6 + totalCount * 0.15);
          curvature = ((currentIndex / (totalCount - 1)) - 0.5) * curvatureRange * 2;
          if (isReversed) {
            curvature = -curvature;
          }
        }

        edges.push({
          source: edge.source_node_uuid,
          target: edge.target_node_uuid,
          type: edge.fact_type || edge.name || 'RELATED',
          name: edge.name || edge.fact_type || 'RELATED',
          curvature,
          isSelfLoop: false,
          pairIndex: currentIndex,
          pairTotal: totalCount,
          rawData: {
            ...edge,
            source_name: nodeMap[edge.source_node_uuid]?.name,
            target_name: nodeMap[edge.target_node_uuid]?.name,
          },
        });
      });

      const colorMap = new Map(entityTypes.map((type) => [type.name, type.color]));
      const getColor = (type: string) => colorMap.get(type) || '#D1D1D1';

      const simulation = d3
        .forceSimulation(nodes)
        .force(
          'link',
          d3
            .forceLink<GraphNodeLayout, GraphEdgeLayout>(edges)
            .id((node: GraphNodeLayout) => node.id)
            .distance((edge: GraphEdgeLayout) => {
              const base = 140;
              const multiplier = edge.pairTotal ? 1 + edge.pairTotal * 0.15 : 1;
              return base * multiplier;
            })
            .strength(0.5)
        )
        .force('charge', d3.forceManyBody().strength(-520))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(32))
        .force('x', d3.forceX(width / 2).strength(0.04))
        .force('y', d3.forceY(height / 2).strength(0.04));

      simulationRef.current = simulation;

      const g = svg.append('g');
      svg.call(
        d3
          .zoom<SVGSVGElement, unknown>()
          .extent([
            [0, 0],
            [width, height],
          ])
          .scaleExtent([0.2, 4])
          .on('zoom', (event: ZoomEvent) => {
            g.attr('transform', event.transform.toString());
          })
      );

      const linkGroup = g.append('g').attr('class', 'links');

      const getLinkPath = (edge: GraphEdgeLayout) => {
        const source = edge.source as GraphNodeLayout;
        const target = edge.target as GraphNodeLayout;
        const sx = source.x ?? 0;
        const sy = source.y ?? 0;
        const tx = target.x ?? 0;
        const ty = target.y ?? 0;

        if (edge.isSelfLoop) {
          const loopRadius = 28;
          return `M ${sx} ${sy} C ${sx + loopRadius} ${sy - loopRadius}, ${sx + loopRadius} ${
            sy + loopRadius
          }, ${sx} ${sy}`;
        }

        if (edge.curvature === 0) {
          return `M ${sx},${sy} L ${tx},${ty}`;
        }

        const dx = tx - sx;
        const dy = ty - sy;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const pairTotal = edge.pairTotal ?? 1;
        const offsetRatio = 0.25 + pairTotal * 0.05;
        const baseOffset = Math.max(35, dist * offsetRatio);
        const offsetX = (-dy / dist) * edge.curvature * baseOffset;
        const offsetY = (dx / dist) * edge.curvature * baseOffset;
        const cx = (sx + tx) / 2 + offsetX;
        const cy = (sy + ty) / 2 + offsetY;
        return `M ${sx} ${sy} Q ${cx} ${cy} ${tx} ${ty}`;
      };

      const getLinkMidpoint = (edge: GraphEdgeLayout) => {
        const source = edge.source as GraphNodeLayout;
        const target = edge.target as GraphNodeLayout;
        const sx = source.x ?? 0;
        const sy = source.y ?? 0;
        const tx = target.x ?? 0;
        const ty = target.y ?? 0;

        if (edge.isSelfLoop) {
          return { x: sx + 48, y: sy };
        }

        if (edge.curvature === 0) {
          return { x: (sx + tx) / 2, y: (sy + ty) / 2 };
        }

        const dx = tx - sx;
        const dy = ty - sy;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const pairTotal = edge.pairTotal ?? 1;
        const offsetRatio = 0.25 + pairTotal * 0.05;
        const baseOffset = Math.max(35, dist * offsetRatio);
        const offsetX = (-dy / dist) * edge.curvature * baseOffset;
        const offsetY = (dx / dist) * edge.curvature * baseOffset;
        const cx = (sx + tx) / 2 + offsetX;
        const cy = (sy + ty) / 2 + offsetY;

        const midX = 0.25 * sx + 0.5 * cx + 0.25 * tx;
        const midY = 0.25 * sy + 0.5 * cy + 0.25 * ty;
        return { x: midX, y: midY };
      };
      const link = linkGroup
        .selectAll('path')
        .data(edges)
        .enter()
        .append('path')
        .attr('stroke', '#5A5A5A')
        .attr('stroke-width', 1.4)
        .attr('fill', 'none')
        .style('cursor', 'pointer')
        .on('click', (event: PointerEvent, edge: GraphEdgeLayout) => {
          event.stopPropagation();
          link.attr('stroke', '#5A5A5A').attr('stroke-width', 1.4);
          linkLabelBg.attr('fill', 'rgba(5,5,5,0.88)');
          linkLabels.attr('fill', '#BDBDBD');
          d3
            .select(event.currentTarget as SVGPathElement)
            .attr('stroke', '#FFFFFF')
            .attr('stroke-width', 2.6);
          setSelectedItem({ type: 'edge', data: edge.rawData });
        });

      const linkLabelBg = linkGroup
        .selectAll('rect')
        .data(edges)
        .enter()
        .append('rect')
        .attr('fill', 'rgba(5,5,5,0.88)')
        .attr('rx', 3)
        .attr('ry', 3)
        .style('pointer-events', 'all')
        .style('display', showEdgeLabels ? 'block' : 'none')
        .on('click', (event: PointerEvent, edge: GraphEdgeLayout) => {
          event.stopPropagation();
          link.attr('stroke', '#5A5A5A').attr('stroke-width', 1.4);
          linkLabelBg.attr('fill', 'rgba(5,5,5,0.88)');
          linkLabels.attr('fill', '#BDBDBD');
          link
            .filter((item: GraphEdgeLayout) => item === edge)
            .attr('stroke', '#FFFFFF')
            .attr('stroke-width', 2.6);
          d3.select(event.currentTarget as SVGRectElement).attr('fill', 'rgba(255,255,255,0.15)');
          setSelectedItem({ type: 'edge', data: edge.rawData });
        });

      const linkLabels = linkGroup
        .selectAll('text')
        .data(edges)
        .enter()
        .append('text')
        .text((edge: GraphEdgeLayout) => edge.name)
        .attr('font-size', '9px')
        .attr('fill', '#BDBDBD')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .style('cursor', 'pointer')
        .style('pointer-events', 'all')
        .style('font-family', 'JetBrains Mono, monospace')
        .style('display', showEdgeLabels ? 'block' : 'none')
        .on('click', (event: PointerEvent, edge: GraphEdgeLayout) => {
          event.stopPropagation();
          link.attr('stroke', '#5A5A5A').attr('stroke-width', 1.4);
          linkLabelBg.attr('fill', 'rgba(5,5,5,0.88)');
          linkLabels.attr('fill', '#BDBDBD');
          link
            .filter((item: GraphEdgeLayout) => item === edge)
            .attr('stroke', '#FFFFFF')
            .attr('stroke-width', 2.6);
          d3.select(event.currentTarget as SVGTextElement).attr('fill', '#FFFFFF');
          setSelectedItem({ type: 'edge', data: edge.rawData });
        });

      linkLabelRef.current = linkLabels;
      linkLabelBgRef.current = linkLabelBg;

      const nodeGroup = g.append('g').attr('class', 'nodes');

      const node = nodeGroup
        .selectAll('circle')
        .data(nodes)
        .enter()
        .append('circle')
        .attr('r', 10)
        .attr('fill', (nodeDatum: GraphNodeLayout) => getColor(nodeDatum.type))
        .attr('stroke', '#E5E5E5')
        .attr('stroke-width', 2)
        .style('cursor', 'pointer')
        .call(
          d3
            .drag<SVGCircleElement, GraphNodeLayout>()
            .on('start', (event: DragEvent, nodeDatum: GraphNodeLayout) => {
              nodeDatum.fx = nodeDatum.x;
              nodeDatum.fy = nodeDatum.y;
              nodeDatum._dragStartX = event.x;
              nodeDatum._dragStartY = event.y;
              nodeDatum._isDragging = false;
            })
            .on('drag', (event: DragEvent, nodeDatum: GraphNodeLayout) => {
              const startX = nodeDatum._dragStartX ?? event.x;
              const startY = nodeDatum._dragStartY ?? event.y;
              const dx = event.x - startX;
              const dy = event.y - startY;
              const distance = Math.sqrt(dx * dx + dy * dy);
              if (!nodeDatum._isDragging && distance > 3) {
                nodeDatum._isDragging = true;
                simulation.alphaTarget(0.3).restart();
              }
              if (nodeDatum._isDragging) {
                nodeDatum.fx = event.x;
                nodeDatum.fy = event.y;
              }
            })
            .on('end', (event: DragEvent, nodeDatum: GraphNodeLayout) => {
              if (nodeDatum._isDragging) {
                simulation.alphaTarget(0);
              }
              nodeDatum.fx = null;
              nodeDatum.fy = null;
              nodeDatum._isDragging = false;
            })
        )
        .on('click', (event: PointerEvent, nodeDatum: GraphNodeLayout) => {
          event.stopPropagation();
          node.attr('stroke', '#E5E5E5').attr('stroke-width', 2);
          link.attr('stroke', '#5A5A5A').attr('stroke-width', 1.4);
          d3
            .select(event.currentTarget as SVGCircleElement)
            .attr('stroke', '#FFFFFF')
            .attr('stroke-width', 3.2);
          link
            .filter(
              (edgeDatum: GraphEdgeLayout) =>
                (edgeDatum.source as GraphNodeLayout).id === nodeDatum.id ||
                (edgeDatum.target as GraphNodeLayout).id === nodeDatum.id
            )
            .attr('stroke', '#FFFFFF')
            .attr('stroke-width', 2.2);
          setSelectedItem({
            type: 'node',
            data: nodeDatum.rawData,
            entityType: nodeDatum.type,
            color: getColor(nodeDatum.type),
          });
        })
        .on('mouseenter', (event: PointerEvent, nodeDatum: GraphNodeLayout) => {
          const currentSelection = selectedItemRef.current;
          if (currentSelection?.type !== 'node' || currentSelection.data.uuid !== nodeDatum.rawData.uuid) {
            d3
              .select(event.currentTarget as SVGCircleElement)
              .attr('stroke', '#BDBDBD')
              .attr('stroke-width', 2.5);
          }
        })
        .on('mouseleave', (event: PointerEvent, nodeDatum: GraphNodeLayout) => {
          const currentSelection = selectedItemRef.current;
          if (currentSelection?.type !== 'node' || currentSelection.data.uuid !== nodeDatum.rawData.uuid) {
            d3
              .select(event.currentTarget as SVGCircleElement)
              .attr('stroke', '#E5E5E5')
              .attr('stroke-width', 2);
          }
        });

      const nodeLabels = nodeGroup
        .selectAll('text')
        .data(nodes)
        .enter()
        .append('text')
        .text((nodeDatum: GraphNodeLayout) =>
          nodeDatum.name.length > 10 ? `${nodeDatum.name.substring(0, 10)}...` : nodeDatum.name
        )
        .attr('font-size', '10px')
        .attr('fill', '#D4D4D4')
        .attr('font-weight', '500')
        .attr('dx', 14)
        .attr('dy', 4)
        .style('pointer-events', 'none')
        .style('font-family', 'JetBrains Mono, monospace');

      simulation.on('tick', () => {
        link.attr('d', (edge: GraphEdgeLayout) => getLinkPath(edge));

        linkLabels.each((edgeDatum: GraphEdgeLayout, index, nodes) => {
          const mid = getLinkMidpoint(edgeDatum);
          d3.select(nodes[index]).attr('x', mid.x).attr('y', mid.y).attr('transform', '');
        });

        linkLabelBg.each((edgeDatum: GraphEdgeLayout, index, nodes) => {
          const mid = getLinkMidpoint(edgeDatum);
          const textEl = linkLabels.nodes()[index];
          if (!textEl) {
            return;
          }
          const bbox = textEl.getBBox();
          d3.select(nodes[index])
            .attr('x', mid.x - bbox.width / 2 - 4)
            .attr('y', mid.y - bbox.height / 2 - 2)
            .attr('width', bbox.width + 8)
            .attr('height', bbox.height + 4)
            .attr('transform', '');
        });

        node
          .attr('cx', (nodeDatum: GraphNodeLayout) => nodeDatum.x ?? 0)
          .attr('cy', (nodeDatum: GraphNodeLayout) => nodeDatum.y ?? 0);
        nodeLabels
          .attr('x', (nodeDatum: GraphNodeLayout) => nodeDatum.x ?? 0)
          .attr('y', (nodeDatum: GraphNodeLayout) => nodeDatum.y ?? 0);
      });

      svg.on('click', () => {
        setSelectedItem(null);
        node.attr('stroke', '#E5E5E5').attr('stroke-width', 2);
        link.attr('stroke', '#5A5A5A').attr('stroke-width', 1.4);
        linkLabelBg.attr('fill', 'rgba(5,5,5,0.88)');
        linkLabels.attr('fill', '#BDBDBD');
      });
    };

    renderGraph();

    const observer = new ResizeObserver(() => {
      renderGraph();
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      simulationRef.current?.stop();
    };
  }, [entityTypes, graphData, showEdgeLabels]);

  const toggleSelfLoop = (id: string) => {
    setExpandedSelfLoops((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const nodeCount = graphData?.node_count ?? graphData?.nodes?.length ?? 0;
  const edgeCount = graphData?.edge_count ?? graphData?.edges?.length ?? 0;

  const hintVisible = currentPhase === 1 || isSimulating;
  return (
    <>
      {isMaximized && (
        <div
          className="fixed inset-0 z-40 bg-neutral-950/80 backdrop-blur-sm"
          onClick={() => setIsMaximized(false)}
        />
      )}
      <div
        className={cn(
          'relative z-50 overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-950/80 shadow-[0_0_40px_rgba(0,0,0,0.35)]',
          isMaximized ? 'fixed inset-6 z-50' : 'relative'
        )}
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.06),_transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(255,255,255,0.05),_transparent_55%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(#2F2F2F_1px,_transparent_1px)] [background-size:22px_22px] opacity-40" />

        <div className="relative z-10 flex h-full min-h-[420px] flex-col">
          <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-4 text-xs uppercase tracking-[0.2em] text-neutral-400">
            <div className="flex items-center gap-3">
              <span className="text-neutral-200">Logic Graph</span>
              <span className="text-neutral-600">/</span>
              <span className="text-neutral-500">{nodeCount} nodes</span>
              <span className="text-neutral-600">/</span>
              <span className="text-neutral-500">{edgeCount} links</span>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 text-[10px] uppercase tracking-[0.3em] text-neutral-500">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border border-neutral-700 bg-neutral-950 text-neutral-200 focus:ring-0"
                  checked={showEdgeLabels}
                  onChange={(event) => setShowEdgeLabels(event.target.checked)}
                />
                Labels
              </label>
              <button
                type="button"
                onClick={() => onRefresh?.()}
                className="flex items-center gap-2 rounded-full border border-neutral-800 bg-neutral-900/70 px-3 py-1 text-[10px] uppercase tracking-[0.25em] text-neutral-400 transition hover:border-neutral-500 hover:text-white"
              >
                <span className={cn('text-sm', loading ? 'animate-spin' : '')}>R</span>
                Refresh
              </button>
              <button
                type="button"
                onClick={() => setIsMaximized((prev) => !prev)}
                className="flex items-center gap-2 rounded-full border border-neutral-800 bg-neutral-900/70 px-3 py-1 text-[10px] uppercase tracking-[0.25em] text-neutral-400 transition hover:border-neutral-500 hover:text-white"
              >
                <span className="text-sm">{isMaximized ? '-' : '+'}</span>
                Focus
              </button>
            </div>
          </div>

          <div className="relative flex-1" ref={graphContainerRef}>
            <svg ref={graphSvgRef} className="h-full w-full" />

            {hintVisible && (
              <div className="absolute bottom-6 left-1/2 flex -translate-x-1/2 items-center gap-3 rounded-full border border-white/10 bg-neutral-900/80 px-5 py-2 text-xs text-neutral-200 shadow-[0_0_24px_rgba(0,0,0,0.4)]">
                <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-neutral-100" />
                {isSimulating ? 'Graph memory updating' : 'Graph build in progress'}
              </div>
            )}

            {showSimulationFinishedHint && (
              <div className="absolute bottom-16 left-1/2 flex -translate-x-1/2 items-center gap-3 rounded-full border border-white/10 bg-neutral-900/80 px-5 py-2 text-xs text-neutral-200">
                <span className="h-2.5 w-2.5 rounded-full bg-neutral-300" />
                Graph build finished. Refresh to sync the latest nodes.
                <button
                  type="button"
                  onClick={() => setShowSimulationFinishedHint(false)}
                  className="ml-2 rounded-full border border-neutral-700 px-2 py-0.5 text-[10px] uppercase tracking-[0.25em] text-neutral-400"
                >
                  Close
                </button>
              </div>
            )}

            {selectedItem && (
              <div className="absolute right-6 top-16 w-[320px] max-h-[calc(100%-8rem)] overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-950/95 shadow-[0_0_30px_rgba(0,0,0,0.45)]">
                <div className="flex items-center gap-3 border-b border-neutral-800 bg-neutral-900/80 px-4 py-3">
                  <span className="text-xs uppercase tracking-[0.3em] text-neutral-400">
                    {selectedItem.type === 'node' ? 'Node' : 'Relation'}
                  </span>
                  {selectedItem.type === 'node' && (
                    <span
                      className="rounded-full px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-neutral-900"
                      style={{ background: selectedItem.color }}
                    >
                      {selectedItem.entityType}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedItem(null);
                      setExpandedSelfLoops(new Set());
                    }}
                    className="ml-auto text-lg text-neutral-500 transition hover:text-neutral-200"
                  >
                    x
                  </button>
                </div>
                <div className="max-h-[calc(100%-3rem)] overflow-y-auto px-4 py-3 text-xs text-neutral-300">
                  {selectedItem.type === 'node' ? (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-neutral-500">Name</span>
                        <span className="text-right text-neutral-100">{selectedItem.data.name || 'n/a'}</span>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-neutral-500">UUID</span>
                        <span className="text-right font-mono text-[10px] text-neutral-400">
                          {selectedItem.data.uuid}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-neutral-500">Created</span>
                        <span className="text-right text-neutral-200">
                          {formatDateTime(selectedItem.data.created_at)}
                        </span>
                      </div>
                      {selectedItem.data.attributes &&
                        Object.keys(selectedItem.data.attributes).length > 0 && (
                          <div className="rounded-xl border border-neutral-800 bg-neutral-900/70 p-3">
                            <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-500">
                              Attributes
                            </p>
                            <div className="mt-2 space-y-1">
                              {Object.entries(selectedItem.data.attributes).map(([key, value]) => (
                                <div key={key} className="flex items-start justify-between gap-3">
                                  <span className="text-neutral-500">{key}</span>
                                  <span className="text-right text-neutral-200">{String(value ?? 'n/a')}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      {selectedItem.data.summary && (
                        <div className="rounded-xl border border-neutral-800 bg-neutral-900/70 p-3 text-neutral-200">
                          <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-500">Summary</p>
                          <p className="mt-2 text-xs leading-relaxed">{selectedItem.data.summary}</p>
                        </div>
                      )}
                      {selectedItem.data.labels && selectedItem.data.labels.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {selectedItem.data.labels.map((label) => (
                            <span
                              key={label}
                              className="rounded-full border border-neutral-800 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-neutral-400"
                            >
                              {label}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : selectedItem.data.isSelfLoopGroup ? (
                    <div className="space-y-3">
                      <div className="rounded-lg border border-neutral-800 bg-neutral-900/70 px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-neutral-400">
                        {selectedItem.data.source_name} self relations ({selectedItem.data.selfLoopCount ?? 0})
                      </div>
                      <div className="space-y-2">
                        {(selectedItem.data.selfLoopEdges ?? []).map((loop, index) => {
                          const loopId = loop.uuid || `${index}`;
                          const expanded = expandedSelfLoops.has(loopId);
                          return (
                            <div
                              key={loopId}
                              className="rounded-xl border border-neutral-800 bg-neutral-900/60"
                            >
                              <button
                                type="button"
                                className="flex w-full items-center justify-between px-3 py-2 text-left text-xs text-neutral-300"
                                onClick={() => toggleSelfLoop(loopId)}
                              >
                                <span className="font-mono text-[10px] text-neutral-500">#{index + 1}</span>
                                <span className="flex-1 px-2">{loop.name || loop.fact_type || 'RELATED'}</span>
                                <span className="text-neutral-500">{expanded ? '-' : '+'}</span>
                              </button>
                              {expanded && (
                                <div className="space-y-2 px-3 pb-3 text-[11px] text-neutral-300">
                                  {loop.uuid && (
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="text-neutral-500">UUID</span>
                                      <span className="text-right font-mono text-[10px] text-neutral-400">
                                        {loop.uuid}
                                      </span>
                                    </div>
                                  )}
                                  {loop.fact && (
                                    <div className="text-xs leading-relaxed text-neutral-200">{loop.fact}</div>
                                  )}
                                  {loop.fact_type && (
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="text-neutral-500">Type</span>
                                      <span className="text-right text-neutral-200">{loop.fact_type}</span>
                                    </div>
                                  )}
                                  {loop.created_at && (
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="text-neutral-500">Created</span>
                                      <span className="text-right text-neutral-200">
                                        {formatDateTime(loop.created_at)}
                                      </span>
                                    </div>
                                  )}
                                  {loop.episodes && loop.episodes.length > 0 && (
                                    <div className="flex flex-wrap gap-1">
                                      {loop.episodes.map((episode) => (
                                        <span
                                          key={episode}
                                          className="rounded-full border border-neutral-700 px-2 py-0.5 text-[10px] text-neutral-400"
                                        >
                                          {episode}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="rounded-lg border border-neutral-800 bg-neutral-900/70 px-3 py-2 text-xs text-neutral-300">
                        <span className="text-neutral-100">{selectedItem.data.source_name || 'Unknown'}</span>{' '}
                        {'->'}
                        <span className="px-1 text-neutral-400">
                          {selectedItem.data.name || selectedItem.data.fact_type || 'RELATED'}
                        </span>
                        {'->'} <span className="text-neutral-100">{selectedItem.data.target_name || 'Unknown'}</span>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-neutral-500">UUID</span>
                        <span className="text-right font-mono text-[10px] text-neutral-400">
                          {selectedItem.data.uuid}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-neutral-500">Label</span>
                        <span className="text-right text-neutral-200">
                          {selectedItem.data.name || selectedItem.data.fact_type || 'RELATED'}
                        </span>
                      </div>
                      {selectedItem.data.fact_type && (
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-neutral-500">Type</span>
                          <span className="text-right text-neutral-200">{selectedItem.data.fact_type}</span>
                        </div>
                      )}
                      {selectedItem.data.fact && (
                        <div className="rounded-xl border border-neutral-800 bg-neutral-900/70 p-3 text-xs leading-relaxed text-neutral-200">
                          {selectedItem.data.fact}
                        </div>
                      )}
                      {selectedItem.data.episodes && selectedItem.data.episodes.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {selectedItem.data.episodes.map((episode) => (
                            <span
                              key={episode}
                              className="rounded-full border border-neutral-700 px-2 py-0.5 text-[10px] text-neutral-400"
                            >
                              {episode}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-neutral-500">Created</span>
                        <span className="text-right text-neutral-200">
                          {formatDateTime(selectedItem.data.created_at)}
                        </span>
                      </div>
                      {selectedItem.data.valid_at && (
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-neutral-500">Valid From</span>
                          <span className="text-right text-neutral-200">
                            {formatDateTime(selectedItem.data.valid_at)}
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {!graphData && !loading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-sm text-neutral-500">
                <div className="text-3xl text-neutral-700">o</div>
                <p>Waiting for graph data</p>
                <p className="text-xs text-neutral-600">Run the analysis path to generate nodes and links.</p>
              </div>
            )}

            {loading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-sm text-neutral-400">
                <div className="h-10 w-10 animate-spin rounded-full border-2 border-neutral-700 border-t-neutral-200" />
                <p>Loading graph data</p>
              </div>
            )}
          </div>

          {entityTypes.length > 0 && (
            <div className="flex flex-wrap gap-3 border-t border-neutral-800 bg-neutral-950/70 px-5 py-3 text-xs text-neutral-400">
              <span className="mr-2 text-[10px] uppercase tracking-[0.3em] text-neutral-500">Entity types</span>
              {entityTypes.map((type) => (
                <span key={type.name} className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: type.color }} />
                  <span className="text-neutral-300">{type.name}</span>
                  <span className="text-neutral-500">{type.count}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default LogicGraphPanel;
