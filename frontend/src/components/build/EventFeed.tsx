import { Activity, Trash2, Radio } from 'lucide-react'
import { EventItem } from './EventItem'
import type { FeedEvent } from '@/types'

interface EventFeedProps {
  events: FeedEvent[]
  onClear: () => void
}

export function EventFeed({ events, onClear }: EventFeedProps) {
  return (
    <div className="flex flex-col h-full bg-[var(--bg-surface)]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 h-14 border-b border-[var(--border-subtle)] flex-none">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-lg bg-[var(--accent-indigo)]/15 flex items-center justify-center">
            <Radio size={12} className="text-[var(--accent-indigo)]" />
          </div>
          <span className="text-sm font-semibold text-white">Event Feed</span>
          {events.length > 0 && (
            <span className="text-[10px] text-[var(--text-muted)] bg-white/5 px-1.5 py-0.5 rounded-full tabular-nums">
              {events.length}
            </span>
          )}
        </div>
        {events.length > 0 && (
          <button
            onClick={onClear}
            aria-label="Clear events"
            className="w-7 h-7 flex items-center justify-center rounded-lg text-[var(--text-muted)] hover:text-white hover:bg-white/5 transition-all duration-150"
          >
            <Trash2 size={13} />
          </button>
        )}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 px-6 text-center">
            <div className="w-10 h-10 rounded-full bg-white/[0.03] border border-[var(--border-subtle)] flex items-center justify-center">
              <Activity size={16} className="text-[var(--text-muted)]" />
            </div>
            <div>
              <p className="text-xs font-medium text-[var(--text-secondary)]">No events yet</p>
              <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
                Pipeline events stream here live
              </p>
            </div>
          </div>
        ) : (
          <div className="py-2">
            {events.map((event) => (
              <EventItem key={event.id} event={event} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
