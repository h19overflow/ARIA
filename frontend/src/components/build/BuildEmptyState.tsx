import clsx from 'clsx'
import { GitBranch, AlertCircle } from 'lucide-react'
import type { WorkflowStatus } from '@/types'

interface BuildEmptyStateProps {
  status: WorkflowStatus
  error: string | null
  onRetry?: () => void
}

function SkeletonNode({ x, y, w = 96, h = 36 }: { x: number; y: number; w?: number; h?: number }) {
  return (
    <rect
      x={x} y={y} width={w} height={h} rx={7}
      className="skeleton"
      fill="rgba(255,255,255,0.04)"
      stroke="rgba(255,255,255,0.06)"
      strokeWidth={1}
    />
  )
}

function SkeletonEdge({ x1, y1, x2, y2 }: { x1: number; y1: number; x2: number; y2: number }) {
  const dy = y2 - y1
  const d = `M ${x1} ${y1} C ${x1} ${y1 + dy * 0.4}, ${x2} ${y2 - dy * 0.4}, ${x2} ${y2}`
  return <path d={d} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={1.5} strokeDasharray="4 4" />
}

function SkeletonGraph() {
  return (
    <svg width={320} height={220} viewBox="0 0 320 220" className="opacity-60">
      <SkeletonNode x={112} y={16} />
      <SkeletonNode x={52} y={100} />
      <SkeletonNode x={172} y={100} />
      <SkeletonNode x={112} y={184} />
      <SkeletonEdge x1={160} y1={52} x2={100} y2={100} />
      <SkeletonEdge x1={160} y1={52} x2={220} y2={100} />
      <SkeletonEdge x1={100} y1={136} x2={160} y2={184} />
      <SkeletonEdge x1={220} y1={136} x2={160} y2={184} />
    </svg>
  )
}

export function BuildEmptyState({ status, error, onRetry }: BuildEmptyStateProps) {
  if (status === 'failed' && error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-5 p-8 text-center">
        <div className="w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center">
          <AlertCircle size={24} className="text-[var(--color-error)]" />
        </div>
        <div className="space-y-1.5">
          <p className="text-sm font-semibold text-white">Build failed</p>
          <p className="text-xs text-[var(--text-muted)] max-w-xs leading-relaxed">{error}</p>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="btn-ghost text-xs px-4 py-2"
          >
            Try again
          </button>
        )}
      </div>
    )
  }

  const isActive = status === 'building'

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6">
      <div className="relative">
        {isActive && (
          <div className={clsx(
            'absolute inset-0 rounded-full',
            'animate-ping opacity-20',
            'bg-[var(--phase-2)]',
          )} style={{ margin: '-12px' }} />
        )}
        <div className={clsx(
          'w-16 h-16 rounded-full flex items-center justify-center',
          isActive
            ? 'bg-[var(--phase-2-dim)] text-[var(--phase-2)]'
            : 'bg-white/5 text-[var(--text-muted)]',
        )}>
          <GitBranch size={28} />
        </div>
      </div>

      <div className="text-center space-y-1">
        <p className="text-sm font-medium text-[var(--text-secondary)]">
          {isActive ? 'Building in progress...' : 'ARIA is designing your workflow...'}
        </p>
        <p className="text-xs text-[var(--text-muted)]">
          The graph will appear here as nodes are created
        </p>
      </div>

      <SkeletonGraph />
    </div>
  )
}
