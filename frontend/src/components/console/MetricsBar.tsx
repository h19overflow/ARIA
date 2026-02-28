import { RefreshCw, Layers, Hash, Link2 } from "lucide-react";
import type { ARIAState } from "@/types";

interface MetricsBarProps {
  ariaState: ARIAState | null;
}

interface MetricTileProps {
  icon: React.ReactNode;
  label: string;
  value: string | number | undefined;
}

function MetricTile({ icon, label, value }: MetricTileProps) {
  return (
    <div className="glass rounded-xl px-4 py-3 flex items-center gap-3">
      <div className="text-[var(--accent-indigo)] flex-none">{icon}</div>
      <div>
        <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-wide font-medium">
          {label}
        </p>
        <p className="text-sm font-semibold text-white font-mono">
          {value !== undefined && value !== null ? String(value) : "—"}
        </p>
      </div>
    </div>
  );
}

export function MetricsBar({ ariaState }: MetricsBarProps) {
  const execId = ariaState?.execution_result?.execution_id;
  const webhookUrl = ariaState?.webhook_url;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <MetricTile
        icon={<RefreshCw size={14} />}
        label="Fix Attempts"
        value={ariaState?.fix_attempts ?? 0}
      />
      <MetricTile
        icon={<Layers size={14} />}
        label="Nodes Built"
        value={
          ariaState?.nodes_to_build?.length
            ? `${ariaState.node_build_results?.length ?? 0} / ${ariaState.nodes_to_build.length}`
            : ariaState?.node_build_results?.length
        }
      />
      <MetricTile
        icon={<Hash size={14} />}
        label="Execution ID"
        value={execId ? execId.slice(0, 12) + "…" : undefined}
      />
      <MetricTile
        icon={<Link2 size={14} />}
        label="Webhook URL"
        value={webhookUrl ? new URL(webhookUrl).pathname : undefined}
      />
    </div>
  );
}
