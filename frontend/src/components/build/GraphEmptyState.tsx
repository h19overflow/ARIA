import { GitBranch, Loader2, Sparkles } from 'lucide-react'
import clsx from 'clsx'
import type { WorkflowStatus } from '@/types'

interface GraphEmptyStateProps {
  status: WorkflowStatus
  isLoading?: boolean
}

const LOADING_STATUSES: WorkflowStatus[] = ['planning', 'building']

const STATUS_LABELS: Partial<Record<WorkflowStatus, string>> = {
  planning: 'Analyzing your workflow…',
  building: 'Generating nodes…',
}

const EXAMPLE_PROMPTS = [
  'When a Typeform is submitted, save it to Airtable and ping Slack',
  'Every day at 9am, pull from Notion and email a digest',
  'On GitHub PR merge, post to Discord and update Linear',
]

export function GraphEmptyState({ status }: GraphEmptyStateProps) {
  const isActive = LOADING_STATUSES.includes(status)
  const label = STATUS_LABELS[status]

  if (isActive && label) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        {/* Pulsing ring */}
        <div className="relative flex items-center justify-center">
          <div className="absolute w-20 h-20 rounded-full bg-[var(--accent-indigo)]/10 animate-ping" />
          <div className="relative w-14 h-14 rounded-full bg-[var(--accent-indigo)]/15 border border-[var(--accent-indigo)]/30 flex items-center justify-center">
            <Loader2 size={24} className="text-[var(--accent-indigo)] animate-spin" />
          </div>
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-white">{label}</p>
          <p className="text-xs text-[var(--text-muted)] mt-1">The graph will appear shortly</p>
        </div>
        {/* Shimmer skeleton preview */}
        <div className="flex flex-col items-center gap-3 mt-2 opacity-20 pointer-events-none select-none">
          <div className="h-9 w-32 rounded-xl bg-white/10 animate-pulse" />
          <div className="flex gap-8">
            <div className="h-9 w-28 rounded-xl bg-white/10 animate-pulse" />
            <div className="h-9 w-28 rounded-xl bg-white/10 animate-pulse" />
          </div>
          <div className="h-9 w-32 rounded-xl bg-white/10 animate-pulse" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 px-8">
      <div className="w-14 h-14 rounded-2xl bg-[var(--bg-elevated)] border border-[var(--border-muted)] flex items-center justify-center">
        <GitBranch size={24} className="text-[var(--text-muted)]" />
      </div>
      <div className="text-center max-w-xs">
        <p className="text-base font-semibold text-white">No workflow yet</p>
        <p className="text-xs text-[var(--text-muted)] mt-1.5 leading-relaxed">
          Describe an automation below and ARIA will design and deploy it to n8n.
        </p>
      </div>
      <div className="w-full max-w-sm space-y-2">
        {EXAMPLE_PROMPTS.map((p) => (
          <div
            key={p}
            className={clsx(
              'flex items-start gap-2.5 px-3 py-2.5 rounded-xl border border-[var(--border-subtle)]',
              'bg-white/[0.02] text-[var(--text-muted)] text-xs leading-relaxed',
            )}
          >
            <Sparkles size={12} className="flex-none mt-0.5 text-[var(--accent-indigo)] opacity-60" />
            {p}
          </div>
        ))}
      </div>
    </div>
  )
}
