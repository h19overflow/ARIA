import clsx from "clsx";
import { Loader2 } from "lucide-react";
import type { FeedEvent } from "@/types";

interface AgentStatusChipProps {
  events: FeedEvent[];
  status: string;
  nodeProgress: { current: number; total: number } | null;
}

function deriveAgentMessage(events: FeedEvent[]): string | null {
  for (const event of events) {
    if (event.status === "running" && event.message) {
      return event.message;
    }
  }
  return null;
}

export function AgentStatusChip({
  events,
  status,
  nodeProgress,
}: AgentStatusChipProps) {
  if (status !== "building") return null;

  const message = deriveAgentMessage(events);
  if (!message) return null;

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 animate-fade-in">
      <div
        className={clsx(
          "flex items-center gap-2 px-3.5 py-1.5 rounded-full",
          "bg-[var(--bg-elevated)]/90 backdrop-blur-md",
          "border border-[var(--border-muted)]",
          "shadow-md",
        )}
      >
        <Loader2 size={12} className="animate-spin text-[var(--phase-2)]" />
        <span className="text-xs text-[var(--text-secondary)] max-w-[280px] truncate">
          {message}
        </span>
        {nodeProgress && (
          <span className="text-[10px] font-mono text-[var(--text-muted)] ml-1">
            {nodeProgress.current}/{nodeProgress.total}
          </span>
        )}
      </div>
    </div>
  );
}
