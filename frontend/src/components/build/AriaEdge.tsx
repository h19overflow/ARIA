import { memo } from "react";
import { BaseEdge, getBezierPath } from "@xyflow/react";
import type { EdgeProps } from "@xyflow/react";
import type { AriaEdgeData } from "@/hooks/useGraphLayout";

function AriaEdgeInner({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) {
  const { active, done, branch } = (data ?? {}) as AriaEdgeData;

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  const gradientId = `edge-gradient-${id}`;

  return (
    <>
      {/* Gradient definition for active edges */}
      {active && !done && (
        <defs>
          <linearGradient id={gradientId} gradientUnits="userSpaceOnUse" x1={sourceX} y1={sourceY} x2={targetX} y2={targetY}>
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.1">
              <animate attributeName="offset" values="-0.5;1.5" dur="2s" repeatCount="indefinite" />
            </stop>
            <stop offset="30%" stopColor="#10b981" stopOpacity="0.8">
              <animate attributeName="offset" values="-0.2;1.8" dur="2s" repeatCount="indefinite" />
            </stop>
            <stop offset="60%" stopColor="#10b981" stopOpacity="0.1">
              <animate attributeName="offset" values="0.1;2.1" dur="2s" repeatCount="indefinite" />
            </stop>
          </linearGradient>
        </defs>
      )}

      {/* Background track */}
      <BaseEdge
        id={`${id}-bg`}
        path={edgePath}
        style={{
          stroke: done ? "rgba(16,185,129,0.15)" : "rgba(255,255,255,0.06)",
          strokeWidth: 2,
        }}
      />

      {/* Foreground — animated or static */}
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: done
            ? "#10b981"
            : active
              ? `url(#${gradientId})`
              : "rgba(255,255,255,0.12)",
          strokeWidth: done ? 2 : active ? 2.5 : 1.5,
          opacity: done ? 0.7 : 1,
        }}
      />

      {/* Branch label */}
      {branch && (
        <foreignObject
          x={labelX - 20}
          y={labelY - 10}
          width={40}
          height={20}
          className="pointer-events-none"
        >
          <div className="text-[9px] text-amber-400 text-center font-medium">
            {branch}
          </div>
        </foreignObject>
      )}
    </>
  );
}

export const AriaEdge = memo(AriaEdgeInner);
