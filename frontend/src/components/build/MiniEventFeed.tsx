import {
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Info,
} from "lucide-react";
import clsx from "clsx";
import type { FeedEvent } from "@/types";

interface MiniEventFeedProps {
  events: FeedEvent[];
}

const STATUS_CONFIG: Record<
  string,
  { bg: string; border: string; text: string; icon: any }
> = {
  running: {
    bg: "bg-[var(--phase-2)]/10",
    border: "border-[var(--phase-2)]",
    text: "text-[var(--phase-2)]",
    icon: Loader2,
  },
  success: {
    bg: "bg-[var(--color-success)]/10",
    border: "border-[var(--color-success)]",
    text: "text-[var(--color-success)]",
    icon: CheckCircle2,
  },
  error: {
    bg: "bg-[var(--color-error)]/10",
    border: "border-[var(--color-error)]",
    text: "text-[var(--color-error)]",
    icon: XCircle,
  },
  warning: {
    bg: "bg-[var(--color-warning)]/10",
    border: "border-[var(--color-warning)]",
    text: "text-[var(--color-warning)]",
    icon: AlertCircle,
  },
};

const DEFAULT_CONFIG = {
  bg: "bg-white/5",
  border: "border-white/20",
  text: "text-[var(--text-muted)]",
  icon: Info,
};

function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function MiniEventFeed({ events }: MiniEventFeedProps) {
  const visible = events.slice(0, 8);

  return (
    <div className="px-3 py-3 flex flex-col flex-1 min-h-[250px] relative">
      <div className="flex items-center justify-between mb-2 px-1 flex-none">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)]">
          Live Log
        </p>
        {events.length > 0 && (
          <span className="flex items-center gap-1.5 text-[9px] text-[var(--text-muted)]">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--phase-2)] animate-pulse-dot" />
            Live
          </span>
        )}
      </div>

      {visible.length === 0 ? (
        <p className="text-[11px] text-[var(--text-muted)] px-1 py-3 text-center border border-dashed border-white/10 rounded-lg">
          Waiting for events…
        </p>
      ) : (
        <div
          className="space-y-2 overflow-hidden flex-1 relative"
          style={{
            maskImage:
              "linear-gradient(to bottom, black 60%, transparent 100%)",
            WebkitMaskImage:
              "linear-gradient(to bottom, black 60%, transparent 100%)",
          }}
        >
          {visible.map((event) => {
            const conf = STATUS_CONFIG[event.status] ?? DEFAULT_CONFIG;
            const Icon = conf.icon;
            return (
              <div
                key={event.id}
                className={clsx(
                  "flex items-start gap-2.5 py-2 px-2.5 rounded-lg border-l-[3px] animate-slide-right backdrop-blur-sm transition-all",
                  conf.bg,
                  conf.border,
                )}
              >
                <div className={clsx("flex-none mt-0.5", conf.text)}>
                  <Icon
                    size={12}
                    className={event.status === "running" ? "animate-spin" : ""}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] text-white leading-snug break-words">
                    {event.message}
                  </p>
                  <p className="text-[9px] text-[var(--text-muted)] tabular-nums mt-0.5 font-medium">
                    {formatTime(event.timestamp)}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
