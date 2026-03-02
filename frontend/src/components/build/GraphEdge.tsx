import type { TopologyEdge } from "@/types";

interface NodePosition {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface GraphEdgeProps {
  edge: TopologyEdge;
  positions: Record<string, NodePosition>;
  isAnimating: boolean;
  isDone?: boolean;
}

function buildCubicPath(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
): string {
  const dy = y2 - y1;
  const cp1y = y1 + dy * 0.4;
  const cp2y = y2 - dy * 0.4;
  return `M ${x1} ${y1} C ${x1} ${cp1y}, ${x2} ${cp2y}, ${x2} ${y2}`;
}

export function GraphEdge({
  edge,
  positions,
  isAnimating,
  isDone,
}: GraphEdgeProps) {
  const from = positions[edge.from_node];
  const to = positions[edge.to_node];
  if (!from || !to) return null;

  const x1 = from.x + from.width / 2;
  const y1 = from.y + from.height;
  const x2 = to.x + to.width / 2;
  const y2 = to.y;
  const pathD = buildCubicPath(x1, y1, x2, y2);
  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;

  const stroke = isDone
    ? "rgba(16,185,129,0.45)"
    : isAnimating
      ? "rgba(99,102,241,0.75)"
      : "rgba(99,102,241,0.4)";

  return (
    <g>
      {/* Background track */}
      <path
        d={pathD}
        fill="none"
        stroke={isDone ? "rgba(16,185,129,0.1)" : "rgba(255,255,255,0.06)"}
        strokeWidth={2}
      />
      {/* Foreground glowing flow */}
      <path
        d={pathD}
        fill="none"
        stroke={stroke}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeDasharray={isAnimating && !isDone ? "8 6" : undefined}
      >
        {isAnimating && !isDone && (
          <animate
            attributeName="stroke-dashoffset"
            from="14"
            to="0"
            dur="0.6s"
            repeatCount="indefinite"
          />
        )}
      </path>
      {/* Arrowhead */}
      <polygon
        points={`${x2},${y2} ${x2 - 4},${y2 - 8} ${x2 + 4},${y2 - 8}`}
        fill={stroke}
      />
      {/* Branch label */}
      {edge.branch && (
        <text
          x={midX + 5}
          y={midY}
          fontSize={9}
          fill="#f59e0b"
          fontFamily="Inter, sans-serif"
          fontWeight={500}
        >
          {edge.branch}
        </text>
      )}
    </g>
  );
}
