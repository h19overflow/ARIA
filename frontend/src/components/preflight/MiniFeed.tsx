import clsx from 'clsx'
import type { FeedEvent } from '@/types'

interface MiniFeedProps {
  events: FeedEvent[]
}

const STATUS_DOT: Record<FeedEvent['status'], string> = {
  running: 'bg-phase1 animate-pulse-dot',
  success: 'bg-success',
  error: 'bg-error',
  warning: 'bg-warning',
}

export function MiniFeed({ events }: MiniFeedProps) {
  const recent = events.slice(0, 5)

  if (recent.length === 0) {
    return (
      <div className="px-3 py-2">
        <p className="text-[11px] text-white/20 font-mono">Waiting for events...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1 overflow-hidden">
      {recent.map((evt, i) => (
        <div
          key={evt.id}
          className={clsx(
            'flex items-start gap-2 px-3 py-1.5 rounded transition-opacity duration-300',
            i === 0 ? 'opacity-100' : 'opacity-50',
          )}
        >
          <span className={clsx('mt-[5px] w-1.5 h-1.5 rounded-full flex-shrink-0', STATUS_DOT[evt.status])} />
          <span className="text-[11px] font-mono text-white/50 leading-relaxed truncate">{evt.message}</span>
        </div>
      ))}
    </div>
  )
}
