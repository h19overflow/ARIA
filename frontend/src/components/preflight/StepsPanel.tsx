import { Activity } from 'lucide-react'
import type { ARIAState, WorkflowStatus, FeedEvent } from '@/types'
import { StepItem, type StepStatus } from './StepItem'
import { ActivityTimeline } from './ActivityTimeline'

interface StepsPanelProps {
  ariaState: ARIAState | null
  status: WorkflowStatus
  events: FeedEvent[]
  activeNode?: string | null
}

interface StepDef {
  label: string
  description: string
  detailFn: (s: ARIAState) => string | undefined
}

const STEPS: StepDef[] = [
  {
    label: 'Understanding your goal',
    description: 'Parsing what you want to build',
    detailFn: (s) => s.intent ?? s.intent_summary,
  },
  {
    label: 'Checking your connections',
    description: 'Finding the apps you need',
    detailFn: (s) => {
      const resolved = Object.keys(s.resolved_credential_ids ?? {}).length
      const pending = (s.pending_credential_types ?? []).length
      if (resolved === 0 && pending === 0) return undefined
      return `${resolved} found${pending > 0 ? `, ${pending} missing` : ''}`
    },
  },
  {
    label: 'Planning the workflow',
    description: 'Designing the steps to take',
    detailFn: (s) => s.build_blueprint ? `${(s.build_blueprint.required_nodes ?? []).length} steps planned` : undefined,
  },
]

function deriveStepStatuses(ariaState: ARIAState | null, status: WorkflowStatus): StepStatus[] {
  if (!ariaState) {
    const isRunning = status === 'planning'
    return [isRunning ? 'running' : 'idle', 'idle', 'idle']
  }

  const step1Done = Boolean(ariaState.intent || ariaState.intent_summary)
  const step2Done =
    (ariaState.pending_credential_types ?? []).length === 0 &&
    Object.keys(ariaState.resolved_credential_ids ?? {}).length > 0
  const step3Done = ariaState.build_blueprint != null

  const finalOrFailed = status === 'done' || status === 'failed'

  const s1: StepStatus = step1Done ? 'done' : status === 'planning' ? 'running' : 'idle'
  const s2: StepStatus = step2Done
    ? 'done'
    : step1Done && !step2Done && !finalOrFailed
    ? 'running'
    : 'idle'
  const s3: StepStatus = step3Done
    ? 'done'
    : step2Done && !step3Done && !finalOrFailed
    ? 'running'
    : 'idle'

  if (status === 'failed') {
    return [s1, s2 === 'running' ? 'error' : s2, s3 === 'running' ? 'error' : s3]
  }

  return [s1, s2, s3]
}

export function StepsPanel({ ariaState, status, events, activeNode = null }: StepsPanelProps) {
  const stepStatuses = deriveStepStatuses(ariaState, status)
  const activeCount = stepStatuses.filter((s) => s === 'done').length

  return (
    <div className="flex flex-col h-full w-72 flex-shrink-0 border-r border-white/6">
      {/* High-level steps header */}
      <div className="px-4 pt-5 pb-4 border-b border-white/6">
        <div className="flex items-center gap-2 mb-1">
          <Activity size={14} className="text-orange" />
          <span className="text-xs font-mono font-semibold text-orange uppercase tracking-widest">Analysis</span>
        </div>
        <p className="text-[11px] text-white/30 font-mono">{activeCount} of 3 complete</p>
      </div>

      {/* Compact step indicators */}
      <div className="px-4 py-4 border-b border-white/6">
        {STEPS.map((step, i) => (
          <StepItem
            key={i}
            index={i}
            label={step.label}
            description={step.description}
            status={stepStatuses[i]}
            detail={ariaState ? step.detailFn(ariaState) : undefined}
            isLast={i === STEPS.length - 1}
          />
        ))}
      </div>

      {/* Activity Timeline — takes remaining space */}
      <div className="flex-1 overflow-hidden">
        <ActivityTimeline events={events} activeNode={activeNode} status={status} />
      </div>
    </div>
  )
}
