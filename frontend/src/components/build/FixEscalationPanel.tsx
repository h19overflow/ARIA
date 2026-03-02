import { useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  RotateCcw,
  X,
  ExternalLink,
  MessageCircle,
} from "lucide-react";
import clsx from "clsx";

interface FixEscalationError {
  node_name?: string;
  message?: string;
  type?: string | null;
  description?: string | null;
  stack?: string | null;
}

interface FixEscalationPanelProps {
  explanation: string;
  error: FixEscalationError;
  fixAttempts: number;
  n8nUrl: string;
  onAction: (action: "retry" | "replan" | "abort" | "discuss", message?: string) => void;
}

export function FixEscalationPanel({
  explanation,
  error,
  fixAttempts,
  n8nUrl,
  onAction,
}: FixEscalationPanelProps) {
  const [showDetails, setShowDetails] = useState(false);
  const [showDiscuss, setShowDiscuss] = useState(false);
  const [discussMessage, setDiscussMessage] = useState("");

  function handleDiscuss() {
    if (!discussMessage.trim()) return;
    onAction("discuss", discussMessage.trim());
    setDiscussMessage("");
    setShowDiscuss(false);
  }

  return (
    <div className="absolute inset-x-0 bottom-0 z-20 p-4 animate-slide-in">
      <div className="rounded-xl border border-amber-500/30 bg-slate-900/60 backdrop-blur-md shadow-2xl shadow-amber-500/10 p-4 space-y-4">
        {/* Header */}
        <div className="flex items-start gap-3">
          <div className="w-7 h-7 rounded-lg bg-amber-500/15 flex items-center justify-center flex-none mt-0.5">
            <AlertTriangle size={14} className="text-amber-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-amber-400 uppercase tracking-wide mb-1">
              Build failed after {fixAttempts} fix attempt
              {fixAttempts !== 1 ? "s" : ""}
            </p>
            <p className="text-sm text-white leading-relaxed">{explanation}</p>
          </div>
        </div>

        {/* Expandable technical details */}
        <button
          onClick={() => setShowDetails((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-white transition-colors duration-150"
        >
          {showDetails ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          Technical details
        </button>

        {showDetails && (
          <div className="rounded-lg bg-[var(--bg-surface)] border border-[var(--border-muted)] p-3 space-y-1.5 text-[11px] font-mono">
            {error.node_name && (
              <div className="flex gap-2">
                <span className="text-[var(--text-muted)] flex-none">Node</span>
                <span className="text-white">{error.node_name}</span>
              </div>
            )}
            {error.type && (
              <div className="flex gap-2">
                <span className="text-[var(--text-muted)] flex-none">Type</span>
                <span className="text-amber-400">{error.type}</span>
              </div>
            )}
            {error.message && (
              <div className="flex gap-2">
                <span className="text-[var(--text-muted)] flex-none">
                  Error
                </span>
                <span className="text-red-400 break-all">{error.message}</span>
              </div>
            )}
            {error.description && (
              <div className="flex gap-2">
                <span className="text-[var(--text-muted)] flex-none">
                  Detail
                </span>
                <span className="text-[var(--text-secondary)] break-all">
                  {error.description}
                </span>
              </div>
            )}
            {error.stack && (
              <details className="mt-1">
                <summary className="text-[var(--text-muted)] cursor-pointer hover:text-white">
                  Stack trace
                </summary>
                <pre className="mt-1 text-[10px] text-[var(--text-muted)] whitespace-pre-wrap break-all leading-relaxed">
                  {error.stack}
                </pre>
              </details>
            )}
            {n8nUrl && (
              <a
                href={n8nUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[var(--accent-indigo)] hover:underline mt-1"
              >
                <ExternalLink size={10} />
                Open in n8n
              </a>
            )}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => onAction("retry")}
            className={clsx(
              "flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold flex-1 justify-center",
              "bg-[var(--accent-indigo)] text-white hover:bg-indigo-500 active:scale-95 transition-all duration-150",
            )}
          >
            <RefreshCw size={12} />
            Try Again
          </button>
          <button
            onClick={() => onAction("replan")}
            className={clsx(
              "flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold flex-1 justify-center",
              "bg-amber-500/15 text-amber-400 border border-amber-500/30",
              "hover:bg-amber-500/25 active:scale-95 transition-all duration-150",
            )}
          >
            <RotateCcw size={12} />
            Rebuild
          </button>
          <button
            onClick={() => setShowDiscuss((v) => !v)}
            className={clsx(
              "flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold",
              "bg-indigo-500/15 text-indigo-400 border border-indigo-500/30",
              "hover:bg-indigo-500/25 active:scale-95 transition-all duration-150",
            )}
          >
            <MessageCircle size={12} />
            Discuss
          </button>
          <button
            onClick={() => onAction("abort")}
            className={clsx(
              "flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold",
              "bg-white/5 text-[var(--text-muted)] border border-white/10",
              "hover:bg-white/10 active:scale-95 transition-all duration-150",
            )}
          >
            <X size={12} />
            Abort
          </button>
        </div>

        {showDiscuss && (
          <div className="flex gap-2 pt-1">
            <input
              type="text"
              value={discussMessage}
              onChange={(e) => setDiscussMessage(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleDiscuss()}
              placeholder="Ask about this error..."
              className="flex-1 px-3 py-2 rounded-lg text-xs bg-[var(--bg-surface)] border border-[var(--border-muted)] text-white placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-indigo)]"
              autoFocus
            />
            <button
              onClick={handleDiscuss}
              disabled={!discussMessage.trim()}
              className="px-3 py-2 rounded-lg text-xs font-semibold bg-[var(--accent-indigo)] text-white hover:bg-indigo-500 disabled:opacity-40 transition-all duration-150"
            >
              Send
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
