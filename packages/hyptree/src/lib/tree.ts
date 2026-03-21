import Dagre from '@dagrejs/dagre';
import type { Node, Edge } from '@xyflow/react';
import type { TreeData } from '../types';

const NODE_WIDTH = 230;
const NODE_HEIGHT = 200;

export function buildReactFlowGraph(data: TreeData): {
  nodes: Node[];
  edges: Edge[];
} {
  const g = new Dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'TB', nodesep: 50, ranksep: 80 });
  g.setDefaultEdgeLabel(() => ({}));

  const nodes: Node[] = [];
  const edges: Edge[] = [];

  for (const v of data.verticals) {
    g.setNode(v.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    nodes.push({
      id: v.id,
      type: 'vertical',
      data: { ...v, nodeType: 'vertical' },
      position: { x: 0, y: 0 },
    });
  }

  for (const m of data.markets) {
    if (!m.verticalId) continue;
    g.setNode(m.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    g.setEdge(m.verticalId, m.id);
    nodes.push({
      id: m.id,
      type: 'market',
      data: { ...m, nodeType: 'market' },
      position: { x: 0, y: 0 },
    });
    edges.push({
      id: `e-${m.verticalId}-${m.id}`,
      source: m.verticalId,
      target: m.id,
      type: 'smoothstep',
    });
  }

  for (const uc of data.useCases) {
    if (!uc.marketId) continue;
    g.setNode(uc.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    g.setEdge(uc.marketId, uc.id);
    nodes.push({
      id: uc.id,
      type: 'useCase',
      data: { ...uc, nodeType: 'useCase' },
      position: { x: 0, y: 0 },
    });
    edges.push({
      id: `e-${uc.marketId}-${uc.id}`,
      source: uc.marketId,
      target: uc.id,
      type: 'smoothstep',
    });
  }

  for (const w of data.workflows) {
    if (!w.useCaseId) continue;
    g.setNode(w.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    g.setEdge(w.useCaseId, w.id);
    nodes.push({
      id: w.id,
      type: 'workflow',
      data: { ...w, nodeType: 'workflow' },
      position: { x: 0, y: 0 },
    });
    edges.push({
      id: `e-${w.useCaseId}-${w.id}`,
      source: w.useCaseId,
      target: w.id,
      type: 'smoothstep',
    });
  }

  Dagre.layout(g);

  return {
    nodes: nodes.map((n) => {
      const pos = g.node(n.id);
      return {
        ...n,
        position: {
          x: pos.x - NODE_WIDTH / 2,
          y: pos.y - NODE_HEIGHT / 2,
        },
      };
    }),
    edges,
  };
}
