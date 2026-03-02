import { useState, useMemo } from "react";
import { NodeCard } from "./NodeCard";
import { GraphEdge } from "./GraphEdge";
import type { Topology, WorkflowStatus, FeedEvent, ARIAState } from "@/types";

interface NodeGraphProps {
  topology: Topology | null;
  ariaState: ARIAState | null;
  status: WorkflowStatus;
  events: FeedEvent[];
}

export const NODE_W = 140;
export const NODE_H = 52;
const H_GAP = 52;
const V_GAP = 80;

interface NodePosition {
  x: number;
  y: number;
  width: number;
  height: number;
}

function deriveTopologyFromNodesToBuild(
  nodesToBuild: Array<{ node_name: string; connected_to: string[] }>,
): Topology | null {
  if (!nodesToBuild?.length) return null;
  const allNodes = nodesToBuild.map((n) => n.node_name);
  const edges: Array<{
    from_node: string;
    to_node: string;
    branch: string | null;
  }> = [];

  for (const node of nodesToBuild) {
    for (const target of node.connected_to || []) {
      edges.push({ from_node: node.node_name, to_node: target, branch: null });
    }
  }

  const incomingNodes = new Set(edges.map((e) => e.to_node));
  const entryNode = allNodes.find((n) => !incomingNodes.has(n)) ?? allNodes[0];

  const branchCounts = edges.reduce<Record<string, number>>((acc, e) => {
    acc[e.from_node] = (acc[e.from_node] ?? 0) + 1;
    return acc;
  }, {});

  return {
    nodes: allNodes,
    edges,
    entry_node: entryNode,
    branch_nodes: Object.entries(branchCounts)
      .filter(([, count]) => count > 1)
      .map(([n]) => n),
  };
}

function deriveTopologyFromWorkflowJson(
  workflowJson: Record<string, unknown>,
): Topology | null {
  const nodes = workflowJson?.nodes as
    | Array<{ name: string; type: string }>
    | undefined;
  const connections = workflowJson?.connections as
    | Record<string, { main?: Array<Array<{ node: string }>> }>
    | undefined;
  if (!nodes?.length) return null;
  const nodeNames = nodes.map((n) => n.name);
  const edges: Array<{
    from_node: string;
    to_node: string;
    branch: string | null;
  }> = [];
  for (const [fromNode, conn] of Object.entries(connections ?? {})) {
    for (const outputBranch of conn.main ?? []) {
      for (const target of outputBranch) {
        edges.push({ from_node: fromNode, to_node: target.node, branch: null });
      }
    }
  }
  const incomingNodes = new Set(edges.map((e) => e.to_node));
  const entryNode =
    nodeNames.find((n) => !incomingNodes.has(n)) ?? nodeNames[0];
  const branchCounts = edges.reduce<Record<string, number>>((acc, e) => {
    acc[e.from_node] = (acc[e.from_node] ?? 0) + 1;
    return acc;
  }, {});
  return {
    nodes: nodeNames,
    edges,
    entry_node: entryNode,
    branch_nodes: Object.entries(branchCounts)
      .filter(([, c]) => c > 1)
      .map(([n]) => n),
  };
}

function computeLayout(topology: Topology): Record<string, NodePosition> {
  const positions: Record<string, NodePosition> = {};
  const visited = new Set<string>();
  const levels: string[][] = [];

  function bfs(root: string) {
    const queue: Array<{ node: string; level: number }> = [
      { node: root, level: 0 },
    ];
    while (queue.length > 0) {
      const item = queue.shift()!;
      if (visited.has(item.node)) continue;
      visited.add(item.node);
      if (!levels[item.level]) levels[item.level] = [];
      levels[item.level].push(item.node);
      const children = topology.edges
        .filter((e) => e.from_node === item.node)
        .map((e) => e.to_node);
      for (const child of children)
        queue.push({ node: child, level: item.level + 1 });
    }
  }

  bfs(topology.entry_node);
  for (const node of topology.nodes) {
    if (!visited.has(node)) levels[levels.length] = [node];
  }

  for (let row = 0; row < levels.length; row++) {
    const cols = levels[row];
    const totalW = cols.length * NODE_W + (cols.length - 1) * H_GAP;
    const startX = -totalW / 2;
    for (let col = 0; col < cols.length; col++) {
      positions[cols[col]] = {
        x: startX + col * (NODE_W + H_GAP),
        y: row * (NODE_H + V_GAP),
        width: NODE_W,
        height: NODE_H,
      };
    }
  }
  return positions;
}

function deriveActiveNode(
  events: FeedEvent[],
  knownNodes: string[],
): string | null {
  const nodeEvents = events.filter(
    (e) => e.stage === "build" || e.stage === "fix" || e.stage === "test",
  );
  if (nodeEvents.length === 0) return null;
  const latest = nodeEvents[0];
  return knownNodes.find((name) => latest.message.includes(name)) ?? null;
}

export function NodeGraph({
  topology,
  ariaState,
  status,
  events,
}: NodeGraphProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const isAnimating = status === "building";

  const effectiveTopology = useMemo(() => {
    if (ariaState?.workflow_json) {
      const derived = deriveTopologyFromWorkflowJson(
        ariaState.workflow_json as Record<string, unknown>,
      );
      if (derived) return derived;
    }
    if (ariaState?.nodes_to_build?.length) {
      const derived = deriveTopologyFromNodesToBuild(
        ariaState.nodes_to_build as Array<{
          node_name: string;
          connected_to: string[];
        }>,
      );
      if (derived) return derived;
    }
    return topology;
  }, [ariaState?.workflow_json, ariaState?.nodes_to_build, topology]);

  const deployedNodes = useMemo(() => {
    const jsonNodes =
      (ariaState?.workflow_json?.nodes as
        | Array<{ name: string }>
        | undefined) ?? [];
    return new Set(jsonNodes.map((n) => n.name));
  }, [ariaState?.workflow_json]);

  const activeNode = deriveActiveNode(events, effectiveTopology?.nodes ?? []);

  const { positions, svgW, svgH } = useMemo(() => {
    if (!effectiveTopology || effectiveTopology.nodes.length === 0)
      return { positions: {}, svgW: 400, svgH: 200 };
    const pos = computeLayout(effectiveTopology);
    const xs = Object.values(pos).map((p) => p.x);
    const ys = Object.values(pos).map((p) => p.y);
    const minX = Math.min(...xs) - 48;
    const maxX = Math.max(...xs) + NODE_W + 48;
    const minY = Math.min(...ys) - 28;
    const maxY = Math.max(...ys) + NODE_H + 28;
    const offset = -minX;
    const offsetPos: Record<string, NodePosition> = {};
    for (const [k, v] of Object.entries(pos)) {
      offsetPos[k] = { ...v, x: v.x + offset, y: v.y + Math.abs(minY) };
    }
    return {
      positions: offsetPos,
      svgW: maxX - minX,
      svgH: maxY - minY + Math.abs(minY),
    };
  }, [effectiveTopology]);

  if (!effectiveTopology) {
    return (
      <div className="w-full h-full overflow-auto flex items-start justify-center pt-6" />
    );
  }

  return (
    <div className="w-full h-full overflow-auto flex items-start justify-center pt-6">
      <svg
        width={svgW}
        height={svgH}
        viewBox={`0 0 ${svgW} ${svgH}`}
        className="overflow-visible"
      >
        {effectiveTopology.edges.map((edge, i) => (
          <GraphEdge
            key={i}
            edge={edge}
            positions={positions}
            isAnimating={isAnimating}
            isDone={status === "done"}
          />
        ))}
        {effectiveTopology.nodes.map((name) => (
          <NodeCard
            key={name}
            name={name}
            isEntry={name === effectiveTopology.entry_node}
            isBranch={effectiveTopology.branch_nodes.includes(name)}
            x={positions[name]?.x ?? 0}
            y={positions[name]?.y ?? 0}
            width={NODE_W}
            height={NODE_H}
            isAnimating={isAnimating}
            isActive={activeNode === name}
            isDone={status === "done"}
            isDeployed={deployedNodes.has(name) || status === "done"}
            onHover={setHoveredNode}
            hoveredNode={hoveredNode}
          />
        ))}
        {hoveredNode && positions[hoveredNode] && (
          <foreignObject
            x={positions[hoveredNode].x}
            y={positions[hoveredNode].y - 34}
            width={160}
            height={28}
          >
            <div className="bg-[var(--bg-elevated)] border border-[var(--border-muted)] rounded-md px-2 py-1 text-[10px] text-white truncate shadow-lg">
              {hoveredNode}
            </div>
          </foreignObject>
        )}
      </svg>
    </div>
  );
}
