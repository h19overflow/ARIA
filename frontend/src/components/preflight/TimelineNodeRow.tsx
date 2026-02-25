import clsx from 'clsx'
import { Check, X, Circle } from 'lucide-react'
import type { TimelineNode } from './timeline-constants'
import { NODE_LABELS } from './timeline-constants'

interface TimelineNodeRowProps {
  node: TimelineNode
  isLast: boolean
}

function formatDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
}

function NodeIndicator({ status }: { status: TimelineNode['status'] }) {
  if (status === 'done') {
    return (
      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-success/20 border border-success/40">
        <Check size={10} className="text-success" strokeWidth={3} />
      </span>
    )
  }
  if (status === 'running') {
    return (
      <span className="relative flex items-center justify-center w-5 h-5 rounded-full bg-orange/20 border border-orange/50">
        <Circle size={7} className="text-orange fill-orange" />
        <span className="absolute inset-0 rounded-full animate-pulse-dot bg-orange/20" />
      </span>
    )
  }
  if (status === 'error') {
    return (
      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-error/20 border border-error/40">
        <X size={10} className="text-error" strokeWidth={3} />
      </span>
    )
  }
  return (
    <span className="flex items-center justify-center w-5 h-5 rounded-full border border-white/10">
      <Circle size={5} className="text-white/20" />
    </span>
  )
}

function ToolChips({ tools, status }: { tools: string[]; status: TimelineNode['status'] }) {
  if (tools.length === 0 || status === 'pending') return null

  return (
    <div className="flex flex-wrap gap-1 mt-1.5">
      {tools.map((tool) => (
        <span
          key={tool}
          className={clsx(
            'inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-mono leading-tight',
            status === 'running'
              ? 'bg-orange/10 text-orange/80 border border-orange/20'
              : 'bg-white/[0.04] text-white/40 border border-white/6',
          )}
        >
          {tool}
        </span>
      ))}
    </div>
  )
}

export function TimelineNodeRow({ node, isLast }: TimelineNodeRowProps) {
  const isExpanded = node.status === 'running' || node.status === 'done'

  return (
    <div className={clsx('flex gap-2.5 animate-fade-in', node.status === 'pending' && 'opacity-40')}>
      {/* Left rail: indicator + connector */}
      <div className="flex flex-col items-center pt-0.5">
        <NodeIndicator status={node.status} />
        {!isLast && (
          <div
            className={clsx(
              'w-px flex-1 mt-1 min-h-[12px] transition-colors duration-500',
              node.status === 'done' ? 'bg-success/25' : 'bg-white/6',
            )}
          />
        )}
      </div>

      {/* Right: content */}
      <div className={clsx('flex-1 min-w-0 pb-3', isLast && 'pb-0')}>
        <div className="flex items-center justify-between gap-2">
          <span
            className={clsx(
              'text-xs font-medium truncate transition-colors duration-300',
              node.status === 'done' && 'text-white/80',
              node.status === 'running' && 'text-orange',
              node.status === 'pending' && 'text-white/30',
              node.status === 'error' && 'text-error',
            )}
          >
            {NODE_LABELS[node.name]}
          </span>

          <span className="flex-shrink-0 text-[10px] font-mono text-white/30">
            {node.status === 'done' && node.durationMs != null && formatDuration(node.durationMs)}
            {node.status === 'running' && <span className="text-orange animate-pulse-dot">running</span>}
            {node.status === 'pending' && 'pending'}
          </span>
        </div>

        {isExpanded && <ToolChips tools={node.tools} status={node.status} />}

        {node.message && isExpanded && (
          <p className="text-[10px] text-white/35 font-mono mt-1 truncate">{node.message}</p>
        )}

        {node.status === 'running' && (
          <div className="mt-2 h-0.5 w-full rounded-full bg-white/6 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-orange/50 via-orange to-orange/50"
              style={{ width: '35%', animation: 'scanLine 1.4s ease-in-out infinite' }}
            />
          </div>
        )}
      </div>
    </div>
  )
}
