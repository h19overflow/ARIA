import clsx from "clsx";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import type { WorkflowStatus, ARIAState } from "@/types";

interface BuildHeaderProps {
  status: WorkflowStatus;
  ariaState: ARIAState | null;
}

const STATUS_META: Record<string, { label: string; sub: string }> = {
  idle: { label: "Starting up…", sub: "Preparing to build your workflow" },
  building: {
    label: "Building your workflow…",
    sub: "Assembling nodes and connections",
  },
  done: {
    label: "Workflow created!",
    sub: "Deployed as inactive draft in n8n",
  },
  failed: { label: "Build failed", sub: "Something went wrong during build" },
};

const isActive = (s: WorkflowStatus) => s === "building";

export function BuildHeader({ status, ariaState }: BuildHeaderProps) {
  const meta = STATUS_META[status] ?? STATUS_META.idle;
  const PhaseIndicator = () => {
    if (ariaState?.nodes_to_build?.length) {
      const current = ariaState.node_build_results?.length ?? 0;
      const total = ariaState.nodes_to_build.length;
      return (
        <span className="text-[10px] text-[var(--text-muted)] bg-white/5 px-1.5 py-0.5 rounded-full">
          node {current}/{total}
        </span>
      );
    }
    return null;
  };

  return (
    <header className="flex-none border-b border-[var(--border-subtle)] phase-2-tint">
      <div className="flex items-center gap-3 px-5 py-3">
        {/* Phase indicator dot */}
        <div
          className={clsx(
            "w-8 h-8 rounded-lg flex items-center justify-center flex-none",
            status === "done" && "bg-[var(--phase-2)]/20 text-[var(--phase-2)]",
            status === "failed" && "bg-red-500/10 text-[var(--color-error)]",
            isActive(status) && "bg-[var(--phase-2)]/15 text-[var(--phase-2)]",
            status === "idle" && "bg-white/5 text-[var(--text-muted)]",
          )}
        >
          {isActive(status) && <Loader2 size={15} className="animate-spin" />}
          {status === "done" && <CheckCircle2 size={15} />}
          {status === "failed" && <XCircle size={15} />}
          {status === "idle" && <span className="text-xs font-bold">2</span>}
        </div>

        {/* Label */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-widest text-[var(--phase-2)] opacity-70">
              Phase 2
            </span>
            <PhaseIndicator />
          </div>
          <p className="text-sm font-semibold text-white leading-tight">
            {meta.label}
          </p>
        </div>

        {/* Sub label */}
        <p className="hidden sm:block text-xs text-[var(--text-muted)] text-right flex-none max-w-[180px]">
          {meta.sub}
        </p>
      </div>

      {/* Progress bar — only when active */}
      {isActive(status) && (
        <div className="h-[2px] bg-white/5 overflow-hidden">
          <div className="h-full bg-gradient-to-r from-[var(--phase-2)] to-emerald-300 animate-pulse w-1/3 rounded-full" />
        </div>
      )}
    </header>
  );
}
