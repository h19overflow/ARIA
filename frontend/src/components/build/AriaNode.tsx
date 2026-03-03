import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";
import clsx from "clsx";
import {
  COLOR_MAP,
  COLOR_ICONS,
  formatNodeLabel,
} from "./nodeCardUtils";
import type { AriaNodeData } from "@/hooks/useGraphLayout";

function AriaNodeInner({ data }: NodeProps) {
  const { label, color, status, isEntry, isBranch } = data as AriaNodeData;
  const colors = COLOR_MAP[color];
  const icon = COLOR_ICONS[color];

  const isActive = status === "active";
  const isDone = status === "done";
  const isFailed = status === "failed";
  const isIdle = status === "idle";

  return (
    <>
      <Handle type="target" position={Position.Left} className="!bg-transparent !border-0 !w-2 !h-2" />

      <div
        className={clsx(
          "relative flex items-center gap-2.5 px-3 py-2.5 rounded-xl border transition-all duration-300 cursor-pointer select-none",
          "min-w-[160px] max-w-[200px]",
          isIdle && "opacity-40 border-white/10 bg-[var(--bg-elevated)]",
          isActive && "opacity-100 border-transparent shadow-lg",
          isDone && "opacity-100 border-white/10 bg-[var(--bg-elevated)]",
          isFailed && "opacity-100 border-red-500/30 bg-red-950/30",
        )}
        style={
          isActive
            ? {
                background: colors.fill,
                borderColor: colors.accent,
                boxShadow: `0 0 24px ${colors.glow}`,
              }
            : undefined
        }
      >
        {/* Active glow ring */}
        {isActive && (
          <div
            className="absolute -inset-1 rounded-xl animate-glow-pulse pointer-events-none"
            style={{
              border: `1.5px solid ${colors.accent}`,
              opacity: 0.5,
            }}
          />
        )}

        {/* Icon */}
        <div
          className="flex-none w-8 h-8 rounded-lg flex items-center justify-center text-sm"
          style={{ background: `${colors.accent}15` }}
        >
          {icon}
        </div>

        {/* Label + badges */}
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-[var(--text-primary)] truncate">
            {formatNodeLabel(label)}
          </p>
          <div className="flex items-center gap-1 mt-0.5">
            {isEntry && (
              <span className="text-[9px] font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-400/10 px-1.5 py-px rounded">
                IN
              </span>
            )}
            {isBranch && (
              <span className="text-[9px] text-orange-400">&#x2442;</span>
            )}
            {isDone && (
              <span className="text-[9px] text-emerald-400">&#x2713;</span>
            )}
            {isFailed && (
              <span className="text-[9px] text-red-400">&#x2715;</span>
            )}
          </div>
        </div>
      </div>

      <Handle type="source" position={Position.Right} className="!bg-transparent !border-0 !w-2 !h-2" />
    </>
  );
}

export const AriaNode = memo(AriaNodeInner);
