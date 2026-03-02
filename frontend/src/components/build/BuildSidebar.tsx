import { BuildTimeline } from './BuildTimeline'
import { LiveMetrics } from './LiveMetrics'
import { MiniEventFeed } from './MiniEventFeed'
import type { ARIAState, WorkflowStatus, FeedEvent } from '@/types'

interface BuildSidebarProps {
  ariaState: ARIAState | null
  status: WorkflowStatus
  events: FeedEvent[]
}

function Divider() {
  return <div className="h-px bg-[var(--border-subtle)] mx-3" />
}

export function BuildSidebar({ ariaState, status, events }: BuildSidebarProps) {
  return (
    <aside className="w-72 flex-none border-l border-[var(--border-subtle)] flex flex-col overflow-y-auto">
      <BuildTimeline status={status} events={events} />
      <Divider />
      <LiveMetrics ariaState={ariaState} status={status} />
      <Divider />
      <MiniEventFeed events={events} />
    </aside>
  )
}
