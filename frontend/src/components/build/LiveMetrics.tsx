import type { ARIAState, WorkflowStatus } from "@/types";

interface LiveMetricsProps {
  ariaState: ARIAState | null;
  status: WorkflowStatus;
}

interface MetricRowProps {
  label: string;
  value: string;
  mono?: boolean;
}

function MetricRow({ label, value, mono }: MetricRowProps) {
  return (
    <div className="flex items-center justify-between gap-2 py-1.5">
      <span className="text-[11px] text-[var(--text-muted)]">{label}</span>
      <span
        className={`text-[11px] text-[var(--text-secondary)] text-right ${mono ? "font-mono" : "font-medium"} max-w-[120px] truncate`}
      >
        {value}
      </span>
    </div>
  );
}

const STATUS_LABEL: Partial<Record<WorkflowStatus, string>> = {
  idle: "Idle",
  building: "Building...",
  done: "Done",
  failed: "Failed",
};

export function LiveMetrics({ ariaState, status }: LiveMetricsProps) {
  const nodesBuilt = ariaState?.node_build_results?.length ?? 0;
  const totalNodes = ariaState?.nodes_to_build?.length;

  return (
    <div className="px-3 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)] mb-1 px-1">
        Metrics
      </p>
      <div className="divide-y divide-white/5">
        <MetricRow label="Status" value={STATUS_LABEL[status] ?? status} />
        {totalNodes !== undefined && (
          <MetricRow
            label="Nodes Built"
            value={`${nodesBuilt} / ${totalNodes}`}
          />
        )}
      </div>
    </div>
  );
}
