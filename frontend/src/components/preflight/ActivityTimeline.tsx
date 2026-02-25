import { useMemo } from 'react'
import { Activity } from 'lucide-react'
import type { FeedEvent, WorkflowStatus } from '@/types'
import { PREFLIGHT_NODES, NODE_TOOLS } from './timeline-constants'
import type { TimelineNode, TimelineNodeStatus } from './timeline-constants'
import { TimelineNodeRow } from './TimelineNodeRow'

interface ActivityTimelineProps {
  events: FeedEvent[]
  activeNode: string | null
  status: WorkflowStatus
}

function deriveNodeStatus(
  nodeName: string,
  activeNode: string | null,
  doneNodes: Set<string>,
  errorNodes: Set<string>,
): TimelineNodeStatus {
  if (errorNodes.has(nodeName)) return 'error'
  if (doneNodes.has(nodeName)) return 'done'
  if (activeNode === nodeName) return 'running'
  return 'pending'
}

function buildTimelineNodes(
  events: FeedEvent[],
  activeNode: string | null,
  status: WorkflowStatus,
): TimelineNode[] {
  const doneNodes = new Set<string>()
  const errorNodes = new Set<string>()
  const nodeTools = new Map<string, string[]>()
  const nodeDurations = new Map<string, number>()
  const nodeMessages = new Map<string, string>()

  for (const evt of events) {
    if (!evt.nodeName) continue
    if (evt.eventType === 'node_done') {
      if (evt.status === 'error') {
        errorNodes.add(evt.nodeName)
      } else {
        doneNodes.add(evt.nodeName)
      }
    }
    if (evt.tools && evt.tools.length > 0) nodeTools.set(evt.nodeName, evt.tools)
    if (evt.durationMs != null) nodeDurations.set(evt.nodeName, evt.durationMs)
    if (evt.message) nodeMessages.set(evt.nodeName, evt.message)
  }

  if (status === 'done') {
    for (const name of PREFLIGHT_NODES) doneNodes.add(name)
  }

  return PREFLIGHT_NODES.map((name) => ({
    name,
    status: deriveNodeStatus(name, activeNode, doneNodes, errorNodes),
    tools: nodeTools.get(name) ?? NODE_TOOLS[name],
    durationMs: nodeDurations.get(name),
    message: nodeMessages.get(name),
  }))
}

export function ActivityTimeline({ events, activeNode, status }: ActivityTimelineProps) {
  const nodes = useMemo(
    () => buildTimelineNodes(events, activeNode, status),
    [events, activeNode, status],
  )

  const doneCount = nodes.filter((n) => n.status === 'done').length

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between border-b border-white/6">
        <div className="flex items-center gap-2">
          <Activity size={12} className="text-orange" />
          <span className="text-[10px] font-mono font-semibold text-orange uppercase tracking-widest">
            Activity
          </span>
        </div>
        <span className="text-[10px] font-mono text-white/25">
          {doneCount}/{PREFLIGHT_NODES.length}
        </span>
      </div>

      {/* Node list */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {nodes.map((node, i) => (
          <TimelineNodeRow key={node.name} node={node} isLast={i === nodes.length - 1} />
        ))}
      </div>
    </div>
  )
}
