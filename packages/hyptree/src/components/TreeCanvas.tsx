'use client';

import { useEffect, useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { buildReactFlowGraph } from '@/lib/tree';
import { ScoreBadge } from './ScoreBadge';
import type { TreeData, AnyNode, Vertical, Market, UseCase, Workflow, RatingLevel } from '@/types';

// --- Shared sub-components ---

// Rating 1–5: colour ramp red → amber → green
const RATING_COLORS: Record<string, string> = {
  '1': 'bg-red-100 text-red-700',
  '2': 'bg-orange-100 text-orange-700',
  '3': 'bg-amber-100 text-amber-700',
  '4': 'bg-lime-100 text-lime-700',
  '5': 'bg-green-100 text-green-700',
};

function RatingGrid({ marketNeed, willingnessToPay, technicalFeasibility, regulatoryFeasibility, easeOfEntry }: {
  marketNeed: RatingLevel;
  willingnessToPay: RatingLevel;
  technicalFeasibility: RatingLevel;
  regulatoryFeasibility: RatingLevel;
  easeOfEntry: RatingLevel;
}) {
  const items = [
    { label: 'Need', value: marketNeed },
    { label: 'WTP', value: willingnessToPay },
    { label: 'Tech', value: technicalFeasibility },
    { label: 'Reg', value: regulatoryFeasibility },
    { label: 'Ease', value: easeOfEntry },
  ].filter((i) => i.value);
  if (items.length === 0) return null;
  return (
    <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 mt-1.5">
      {items.map(({ label, value }) => (
        <div key={label} className="flex items-center gap-1">
          <span className="text-[9px] opacity-50 w-10 shrink-0">{label}</span>
          <span className={`text-[9px] font-medium rounded px-1 py-0.5 ${RATING_COLORS[value] ?? 'bg-white/20 text-white'}`}>{value}/5</span>
        </div>
      ))}
    </div>
  );
}

function TextFields({ currentDeployments, alternativeSolutions, dark }: {
  currentDeployments: string;
  alternativeSolutions: string;
  dark?: boolean;
}) {
  const muted = dark ? 'opacity-40' : 'text-gray-400';
  const body = dark ? 'opacity-70' : 'text-gray-600';
  const items = [
    { label: 'Deployments', value: currentDeployments },
    { label: 'Alt. Solutions', value: alternativeSolutions },
  ].filter((i) => i.value);
  if (items.length === 0) return null;
  return (
    <div className="mt-1.5 space-y-0.5">
      {items.map(({ label, value }) => (
        <div key={label} className="flex gap-1 leading-tight">
          <span className={`text-[9px] shrink-0 ${muted}`}>{label}:</span>
          <span className={`text-[9px] truncate ${body}`}>{value}</span>
        </div>
      ))}
    </div>
  );
}

// --- Custom node components ---

function VerticalNode({ data, selected }: NodeProps) {
  const v = data as unknown as Vertical & { nodeType: 'vertical' };
  return (
    <div
      className={`w-[230px] rounded-xl px-4 py-3 shadow-md border-2 cursor-pointer transition-all
        ${selected ? 'border-blue-400 shadow-blue-200 shadow-lg' : 'border-blue-200'}
        bg-gradient-to-br from-blue-600 to-blue-700 text-white`}
    >
      <div className="text-[10px] uppercase tracking-widest opacity-60 mb-0.5">Vertical</div>
      <div className="font-semibold text-sm leading-tight truncate">{v.name}</div>
      {v.description && (
        <div className="text-xs opacity-60 mt-0.5 line-clamp-2 leading-tight">{v.description}</div>
      )}
      <RatingGrid marketNeed={v.marketNeed} willingnessToPay={v.willingnessToPay} technicalFeasibility={v.technicalFeasibility} regulatoryFeasibility={v.regulatoryFeasibility} easeOfEntry={v.easeOfEntry} />
      <TextFields currentDeployments={v.currentDeployments} alternativeSolutions={v.alternativeSolutions} dark />
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <span className="text-[10px] bg-white/20 rounded px-1.5 py-0.5">{v.status}</span>
        {v.priority != null && <span className="text-[10px] opacity-60">P{v.priority}</span>}
        {v.owner && <span className="text-[10px] opacity-60 truncate">{v.owner}</span>}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-blue-300 !border-blue-500" />
    </div>
  );
}

function MarketNode({ data, selected }: NodeProps) {
  const m = data as unknown as Market & { nodeType: 'market' };
  return (
    <div
      className={`w-[230px] rounded-xl px-4 py-3 shadow-md border-2 cursor-pointer transition-all
        ${selected ? 'border-green-400 shadow-green-200 shadow-lg' : 'border-green-200'}
        bg-gradient-to-br from-green-600 to-green-700 text-white`}
    >
      <Handle type="target" position={Position.Top} className="!bg-green-300 !border-green-500" />
      <div className="text-[10px] uppercase tracking-widest opacity-60 mb-0.5">Market</div>
      <div className="font-semibold text-sm leading-tight truncate">{m.name}</div>
      {m.description && (
        <div className="text-xs opacity-60 mt-0.5 line-clamp-2 leading-tight">{m.description}</div>
      )}
      <RatingGrid marketNeed={m.marketNeed} willingnessToPay={m.willingnessToPay} technicalFeasibility={m.technicalFeasibility} regulatoryFeasibility={m.regulatoryFeasibility} easeOfEntry={m.easeOfEntry} />
      <TextFields currentDeployments={m.currentDeployments} alternativeSolutions={m.alternativeSolutions} dark />
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <span className="text-[10px] bg-white/20 rounded px-1.5 py-0.5">{m.status}</span>
        {m.tam !== null && <span className="text-[10px] opacity-60">${m.tam}M TAM</span>}
        {m.priority != null && <span className="text-[10px] opacity-60">P{m.priority}</span>}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-green-300 !border-green-500" />
    </div>
  );
}

function UseCaseNode({ data, selected }: NodeProps) {
  const uc = data as unknown as UseCase & { nodeType: 'useCase' };
  return (
    <div
      className={`w-[230px] rounded-xl px-4 py-3 shadow-md border-2 cursor-pointer transition-all
        ${selected ? 'border-violet-400 shadow-violet-200 shadow-lg' : 'border-violet-200'}
        bg-gradient-to-br from-violet-600 to-violet-700 text-white`}
    >
      <Handle type="target" position={Position.Top} className="!bg-violet-300 !border-violet-500" />
      <div className="text-[10px] uppercase tracking-widest opacity-60 mb-0.5">Use Case</div>
      <div className="font-semibold text-sm leading-tight truncate">{uc.name}</div>
      {uc.description && (
        <div className="text-xs opacity-60 mt-0.5 line-clamp-2 leading-tight">{uc.description}</div>
      )}
      <RatingGrid marketNeed={uc.marketNeed} willingnessToPay={uc.willingnessToPay} technicalFeasibility={uc.technicalFeasibility} regulatoryFeasibility={uc.regulatoryFeasibility} easeOfEntry={uc.easeOfEntry} />
      <TextFields currentDeployments={uc.currentDeployments} alternativeSolutions={uc.alternativeSolutions} dark />
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <span className="text-[10px] bg-white/20 rounded px-1.5 py-0.5">{uc.status}</span>
        {uc.priority != null && <span className="text-[10px] opacity-60">P{uc.priority}</span>}
        {uc.owner && <span className="text-[10px] opacity-60 truncate">{uc.owner}</span>}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-violet-300 !border-violet-500" />
    </div>
  );
}

function WorkflowNode({ data, selected }: NodeProps) {
  const w = data as unknown as Workflow & { nodeType: 'workflow' };
  return (
    <div
      className={`w-[230px] rounded-xl px-4 py-3 shadow-md border-2 cursor-pointer transition-all
        ${selected ? 'border-orange-400 shadow-orange-200 shadow-lg' : 'border-orange-200'}
        bg-white`}
    >
      <Handle type="target" position={Position.Top} className="!bg-orange-300 !border-orange-500" />
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] uppercase tracking-widest text-orange-500">{w.type}</span>
        <ScoreBadge confidence={w.confidence} score={w.score} />
      </div>
      <div className="text-sm font-semibold leading-tight text-gray-800 line-clamp-2">{w.name}</div>
      {w.description && (
        <div className="text-xs text-gray-500 mt-0.5 line-clamp-2 leading-tight">{w.description}</div>
      )}
      <RatingGrid marketNeed={w.marketNeed} willingnessToPay={w.willingnessToPay} technicalFeasibility={w.technicalFeasibility} regulatoryFeasibility={w.regulatoryFeasibility} easeOfEntry={w.easeOfEntry} />
      <TextFields currentDeployments={w.currentDeployments} alternativeSolutions={w.alternativeSolutions} />
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <span className="text-[10px] bg-orange-50 border border-orange-200 text-orange-700 rounded px-1.5 py-0.5">{w.status}</span>
        {w.owner && <span className="text-[10px] text-gray-400 truncate">{w.owner}</span>}
      </div>
    </div>
  );
}

const nodeTypes = {
  vertical: VerticalNode,
  market: MarketNode,
  useCase: UseCaseNode,
  workflow: WorkflowNode,
};

// --- Main canvas ---

interface Props {
  data: TreeData;
  selectedId: string | null;
  onSelect: (node: AnyNode) => void;
}

export function TreeCanvas({ data, selectedId, onSelect }: Props) {
  const { nodes: layoutNodes, edges: layoutEdges } = useMemo(
    () => buildReactFlowGraph(data),
    [data],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutNodes);
  const [edges, , onEdgesChange] = useEdgesState(layoutEdges);

  useEffect(() => {
    const { nodes: n } = buildReactFlowGraph(data);
    setNodes(n);
  }, [data, setNodes]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: { id: string; data: unknown }) => {
      onSelect(node.data as AnyNode);
    },
    [onSelect],
  );

  return (
    <ReactFlow
      nodes={nodes.map((n) => ({ ...n, selected: n.id === selectedId }))}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={handleNodeClick}
      fitView
      fitViewOptions={{ padding: 0.1 }}
      minZoom={0.2}
      maxZoom={2}
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={20} color="#e5e7eb" />
      <Controls />
      <MiniMap
        nodeColor={(n) => {
          if (n.type === 'vertical') return '#2563eb';
          if (n.type === 'market') return '#16a34a';
          if (n.type === 'useCase') return '#7c3aed';
          return '#f97316';
        }}
        maskColor="rgba(0,0,0,0.05)"
      />
    </ReactFlow>
  );
}
