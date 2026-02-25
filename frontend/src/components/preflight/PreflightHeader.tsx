import clsx from 'clsx'
import { CheckCircle2, Loader } from 'lucide-react'
import type { WorkflowStatus, ARIAState } from '@/types'

interface PreflightHeaderProps {
  status: WorkflowStatus
  ariaState: ARIAState | null
  activeNode?: string | null
}

const NODE_DESCRIPTIONS: Record<string, string> = {
  orchestrator: 'Parsing intent and planning nodes',
  credential_scanner: 'Scanning for required credentials',
  credential_guide: 'Building credential setup guide',
  credential_saver: 'Saving your credentials',
  handoff: 'Finalizing build blueprint',
}

function getHeadline(status: WorkflowStatus, ariaState: ARIAState | null): string {
  if (status === 'done') return 'Analysis complete'
  if (status === 'failed') return 'Analysis failed'
  if (status === 'interrupted') return 'One moment — we need your help'
  if (ariaState?.intent) return `Analysing "${ariaState.intent}"...`
  return 'Analysing your requirements...'
}

function getSubline(
  status: WorkflowStatus,
  ariaState: ARIAState | null,
  activeNode: string | null,
): string {
  if (status === 'done') {
    const bp = ariaState?.build_blueprint
    const nodeCount = bp?.required_nodes?.length ?? 0
    return `Ready to build${nodeCount > 0 ? ` • ${nodeCount} steps planned` : ''}`
  }
  if (status === 'failed') return 'Something went wrong. Try again.'
  if (status === 'interrupted') return 'A connection is needed before we can continue'
  if (activeNode && NODE_DESCRIPTIONS[activeNode]) {
    return `Running ${activeNode} — ${NODE_DESCRIPTIONS[activeNode]}`
  }
  return 'ARIA is figuring out exactly what to build and what it needs'
}

export function PreflightHeader({ status, ariaState, activeNode = null }: PreflightHeaderProps) {
  const isDone = status === 'done'
  const isFailed = status === 'failed'

  return (
    <div
      className={clsx(
        'flex items-center gap-4 px-6 py-4 border-b border-white/6',
        'bg-orange/[0.04]',
      )}
    >
      {/* Icon */}
      <div
        className={clsx(
          'flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-xl border',
          isDone && 'bg-success/20 border-success/30',
          isFailed && 'bg-error/20 border-error/30',
          !isDone && !isFailed && 'bg-orange/15 border-orange/30',
        )}
      >
        {isDone ? (
          <CheckCircle2 size={17} className="text-success" />
        ) : (
          <Loader
            size={17}
            className={clsx(
              isFailed ? 'text-error' : 'text-orange',
              !isFailed && !isDone && 'animate-spin-slow',
            )}
          />
        )}
      </div>

      {/* Text */}
      <div className="min-w-0">
        <h1 className="text-sm font-semibold text-white/90 truncate">
          {getHeadline(status, ariaState)}
        </h1>
        <p className="text-xs text-white/40 mt-0.5 truncate">
          {getSubline(status, ariaState, activeNode)}
        </p>
      </div>

      {/* Phase badge */}
      <div className="ml-auto flex-shrink-0">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-orange/15 border border-orange/25 text-[10px] font-mono font-bold text-orange uppercase tracking-widest">
          <span
            className={clsx(
              'w-1.5 h-1.5 rounded-full bg-orange',
              !isDone && !isFailed && 'animate-pulse-dot',
            )}
          />
          Phase 1
        </span>
      </div>
    </div>
  )
}
