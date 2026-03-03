import * as React from "react";
import clsx from "clsx";
import { X, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import type { ARIAState } from "@/types";
import { COLOR_MAP, detectNodeColor, formatNodeLabel } from "./nodeCardUtils";

interface NodeDetailDrawerProps {
  nodeName: string | null;
  ariaState: ARIAState | null;
  onClose: () => void;
}

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({
  title,
  children,
}) => (
  <div>
    <p className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] mb-1">
      {title}
    </p>
    {children}
  </div>
);

function findBuildResult(ariaState: ARIAState | null, nodeName: string) {
  const results = ariaState?.node_build_results;
  if (!Array.isArray(results)) return undefined;
  return results.find((r) => r.node_name === nodeName);
}

function findWorkflowNode(ariaState: ARIAState | null, nodeName: string) {
  const nodes = ariaState?.workflow_json?.nodes as Array<{ name?: string; type?: string; parameters?: unknown }> | undefined;
  if (!Array.isArray(nodes)) return undefined;
  return nodes.find((n) => n.name === nodeName);
}

export function NodeDetailDrawer({
  nodeName,
  ariaState,
  onClose,
}: NodeDetailDrawerProps) {
  if (!nodeName) return null;

  const buildResult = findBuildResult(ariaState, nodeName);
  const workflowNode = findWorkflowNode(ariaState, nodeName);
  const color = detectNodeColor(nodeName);
  const colors = COLOR_MAP[color];

  const hasError = Boolean(buildResult?.validation_errors?.length);
  const isDeployed = Boolean(workflowNode);
  const nodeType = workflowNode?.type ?? "—";

  return (
    <div
      className={clsx(
        "absolute top-0 right-0 h-full w-80 z-30",
        "bg-[var(--bg-surface)] border-l border-[var(--border-muted)]",
        "flex flex-col overflow-hidden",
        "animate-slide-right",
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-subtle)]">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className="w-3 h-3 rounded-full flex-none"
            style={{ background: colors.accent }}
          />
          <h3 className="text-sm font-semibold text-[var(--text-primary)] truncate">
            {formatNodeLabel(nodeName)}
          </h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md hover:bg-white/5 text-[var(--text-muted)] transition-colors"
        >
          <X size={14} />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {/* Status */}
        <Section title="Status">
          <div className="flex items-center gap-2">
            {hasError ? (
              <AlertCircle size={14} className="text-red-400" />
            ) : isDeployed ? (
              <CheckCircle2 size={14} className="text-emerald-400" />
            ) : (
              <Loader2 size={14} className="text-[var(--text-muted)] animate-spin" />
            )}
            <span className="text-xs text-[var(--text-secondary)]">
              {hasError ? "Failed" : isDeployed ? "Deployed" : "Building\u2026"}
            </span>
          </div>
        </Section>

        {/* Type */}
        <Section title="Node type">
          <p className="text-xs font-mono text-[var(--text-secondary)]">
            {nodeType}
          </p>
        </Section>

        {/* Error */}
        {hasError && (
          <Section title="Errors">
            <ul className="text-xs text-red-400 space-y-1">
              {buildResult!.validation_errors.map((err, i) => (
                <li key={i} className="whitespace-pre-wrap">{err}</li>
              ))}
            </ul>
          </Section>
        )}

        {/* Parameters (from deployed workflow JSON) */}
        {workflowNode?.parameters !== undefined && (
          <Section title="Parameters">
            <pre className="text-[10px] text-[var(--text-muted)] bg-[var(--bg-elevated)] rounded-lg p-2 overflow-x-auto max-h-48">
              {JSON.stringify(workflowNode.parameters, null, 2)}
            </pre>
          </Section>
        )}
      </div>
    </div>
  );
}
