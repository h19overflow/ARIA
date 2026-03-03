import * as React from "react";
import { useCallback, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  ReactFlowProvider,
} from "@xyflow/react";
import type { Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { Topology, ARIAState, FeedEvent } from "@/types";
import { useGraphLayout } from "@/hooks/useGraphLayout";
import { AriaNode } from "./AriaNode";
import { AriaEdge } from "./AriaEdge";
import { AgentStatusChip } from "./AgentStatusChip";
import { NodeDetailDrawer } from "./NodeDetailDrawer";

const NODE_TYPES = { ariaNode: AriaNode } as const;
const EDGE_TYPES = { ariaEdge: AriaEdge } as const;

interface BuildCanvasProps {
  topology: Topology | null;
  ariaState: ARIAState | null;
  status: string;
  events: FeedEvent[];
}

function deriveActiveNode(events: FeedEvent[]): string | null {
  for (const event of events) {
    if (event.status === "running" && event.nodeName) {
      return event.nodeName;
    }
  }
  return null;
}

function deriveNodeProgress(
  ariaState: ARIAState | null,
): { current: number; total: number } | null {
  const planned = ariaState?.nodes_to_build?.length;
  if (!planned) return null;
  const built = ariaState?.node_build_results?.length ?? 0;
  return { current: built, total: planned };
}

function deriveEffectiveTopology(
  topology: Topology | null,
  ariaState: ARIAState | null,
): Topology | null {
  if (ariaState?.topology?.nodes?.length) return ariaState.topology;
  return topology;
}

function BuildCanvasInner({
  topology,
  ariaState,
  status,
  events,
}: BuildCanvasProps) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const activeNode = useMemo(() => deriveActiveNode(events), [events]);
  const nodeProgress = useMemo(
    () => deriveNodeProgress(ariaState),
    [ariaState],
  );
  const effectiveTopology = useMemo(
    () => deriveEffectiveTopology(topology, ariaState),
    [topology, ariaState],
  );

  const { nodes, edges } = useGraphLayout(
    effectiveTopology,
    ariaState,
    activeNode,
  );

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      setSelectedNode((prev) => (prev === node.id ? null : node.id));
    },
    [],
  );

  return (
    <div className="relative w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodeClick={handleNodeClick}
        nodeTypes={NODE_TYPES}
        edgeTypes={EDGE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.3}
        maxZoom={2}
        nodesDraggable={false}
        nodesConnectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1.5}
          color="rgba(255,255,255,0.08)"
          style={{ backgroundColor: "#0e0e0e" }}
        />
      </ReactFlow>

      <AgentStatusChip
        events={events}
        status={status}
        nodeProgress={nodeProgress}
      />

      <NodeDetailDrawer
        nodeName={selectedNode}
        ariaState={ariaState}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  );
}

export function BuildCanvas(props: BuildCanvasProps) {
  return (
    <ReactFlowProvider>
      <BuildCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
