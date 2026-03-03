import { useMemo } from "react";
import type { Node, Edge } from "@xyflow/react";
import { Position } from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import type { Topology } from "@/types";
import type { ARIAState } from "@/types";
import { detectNodeColor } from "@/components/build/nodeCardUtils";

const NODE_W = 180;
const NODE_H = 64;
const GRAPH_OPTIONS = { rankdir: "LR" as const, nodesep: 60, ranksep: 120 };

export type NodeStatus = "idle" | "active" | "done" | "failed";

export interface AriaNodeData {
  label: string;
  color: ReturnType<typeof detectNodeColor>;
  status: NodeStatus;
  isEntry: boolean;
  isBranch: boolean;
  nodeName: string;
  [key: string]: unknown;
}

export interface AriaEdgeData {
  branch?: string | null;
  active: boolean;
  done: boolean;
  [key: string]: unknown;
}

function findBuildResult(
  ariaState: ARIAState | null,
  nodeName: string,
): { error?: string; node_json?: unknown } | undefined {
  const results = ariaState?.node_build_results;
  if (!Array.isArray(results)) return undefined;
  return results.find((r) => r.node_name === nodeName);
}

function deriveNodeStatus(
  nodeName: string,
  ariaState: ARIAState | null,
  activeNode: string | null,
): NodeStatus {
  if (activeNode === nodeName) return "active";
  const result = findBuildResult(ariaState, nodeName);
  if (result?.error) return "failed";
  const deployed = (ariaState?.workflow_json?.nodes as Array<{ name?: string }>) ?? [];
  if (deployed.some((n) => n.name === nodeName)) return "done";
  if (result) return "done";
  return "idle";
}

function layoutWithDagre(
  nodes: Node<AriaNodeData>[],
  edges: Edge<AriaEdgeData>[],
): Node<AriaNodeData>[] {
  const g = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  g.setGraph(GRAPH_OPTIONS);

  for (const node of nodes) {
    g.setNode(node.id, { width: NODE_W, height: NODE_H });
  }
  for (const edge of edges) {
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  return nodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    };
  });
}

export function useGraphLayout(
  topology: Topology | null,
  ariaState: ARIAState | null,
  activeNode: string | null,
): { nodes: Node<AriaNodeData>[]; edges: Edge<AriaEdgeData>[] } {
  return useMemo(() => {
    if (!topology?.nodes?.length) return { nodes: [], edges: [] };

    const rfNodes: Node<AriaNodeData>[] = topology.nodes.map((name) => ({
      id: name,
      type: "ariaNode",
      position: { x: 0, y: 0 },
      data: {
        label: name,
        color: detectNodeColor(name),
        status: deriveNodeStatus(name, ariaState, activeNode),
        isEntry: name === topology.entry_node,
        isBranch: topology.branch_nodes?.includes(name) ?? false,
        nodeName: name,
      },
    }));

    const rfEdges: Edge<AriaEdgeData>[] = topology.edges.map((e) => {
      const sourceStatus = deriveNodeStatus(e.from_node, ariaState, activeNode);
      const targetStatus = deriveNodeStatus(e.to_node, ariaState, activeNode);
      return {
        id: `${e.from_node}->${e.to_node}`,
        source: e.from_node,
        target: e.to_node,
        type: "ariaEdge",
        data: {
          branch: e.branch,
          active:
            sourceStatus === "done" &&
            (targetStatus === "active" || targetStatus === "done"),
          done: sourceStatus === "done" && targetStatus === "done",
        },
      };
    });

    const layoutedNodes = layoutWithDagre(rfNodes, rfEdges);
    return { nodes: layoutedNodes, edges: rfEdges };
  }, [topology, ariaState, activeNode]);
}
