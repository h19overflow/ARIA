import { CheckCircle2, XCircle, AlertTriangle, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import type { FeedEvent } from '@/types'

interface EventItemProps {
  event: FeedEvent
}

const STAGE_CONFIG: Record<string, { label: string; className: string }> = {
  preflight: { label: 'Pre', className: 'text-[var(--accent-orange)] bg-orange/10' },
  build:     { label: 'Bld', className: 'text-blue-400 bg-blue-500/10' },
  system:    { label: 'Sys', className: 'text-[var(--text-muted)] bg-white/5' },
}

function StatusIcon({ status }: { status: FeedEvent['status'] }) {
  if (status === 'success') return <CheckCircle2 size={12} className="flex-none text-[var(--color-success)]" />
  if (status === 'error')   return <XCircle size={12} className="flex-none text-[var(--color-error)]" />
  if (status === 'warning') return <AlertTriangle size={12} className="flex-none text-[var(--color-warning)]" />
  return <Loader2 size={12} className="flex-none text-[var(--accent-orange)] animate-spin" />
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function EventItem({ event }: EventItemProps) {
  const config = STAGE_CONFIG[event.stage] ?? STAGE_CONFIG.system

  return (
    <div className="flex items-start gap-2.5 px-4 py-2.5 hover:bg-white/[0.02] transition-colors duration-100 animate-slide-in">
      <StatusIcon status={event.status} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={clsx('text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider', config.className)}>
            {config.label}
          </span>
          <span className="text-[10px] text-[var(--text-muted)] font-mono ml-auto flex-none tabular-nums">
            {formatTime(event.timestamp)}
          </span>
        </div>
        <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed break-words">
          {event.message}
        </p>
      </div>
    </div>
  )
}
