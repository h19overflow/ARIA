import type { WorkflowStatus, FeedEvent } from '@/types'
export interface Step {
  id: string
  label: string
  stages: string[]
  icon?: unknown
}

export type StepStatus = 'pending' | 'running' | 'done' | 'error'

export interface StepState {
  status: StepStatus
  durationMs: number | null
  errorExcerpt: string | null
  firstSeen: Date | null
  lastSeen: Date | null
}

export const BUILD_STEPS: Step[] = [
  { id: 'rag',      label: 'Finding templates',  stages: ['rag'] },
  { id: 'engineer', label: 'Designing workflow',  stages: ['plan', 'build', 'assemble'] },
  { id: 'deploy',   label: 'Deploying to n8n',    stages: ['deploy'] },
  { id: 'test',     label: 'Testing it out',      stages: ['test'] },
  { id: 'fix',      label: 'Fixing issues',       stages: ['fix'] },
  { id: 'activate', label: 'Going live',          stages: ['activate'] },
]

export function deriveStepStates(
  ariaStatus: WorkflowStatus,
  events: FeedEvent[],
  fixAttempts: number,
): Record<string, StepState> {
  const result: Record<string, StepState> = {}

  for (const step of BUILD_STEPS) {
    const stepEvents = events.filter((e) =>
      step.stages.includes(e.stage)
    )
    const timestamps = stepEvents.map((e) => e.timestamp)
    const first = timestamps.length
      ? new Date(Math.min(...timestamps.map((t) => t.getTime())))
      : null
    const last = timestamps.length
      ? new Date(Math.max(...timestamps.map((t) => t.getTime())))
      : null
    const errorEvent = stepEvents.find((e) => e.status === 'error')

    let status: StepStatus = 'pending'
    if (ariaStatus === 'done') {
      status = step.id === 'fix' && fixAttempts === 0 ? 'pending' : 'done'
    } else if (ariaStatus === 'failed' && errorEvent) {
      status = 'error'
    } else if (stepEvents.length > 0) {
      const isCurrentlyRunning =
        (ariaStatus === 'building' && ['rag', 'engineer', 'deploy'].includes(step.id)) ||
        (ariaStatus === 'testing' && step.id === 'test') ||
        (ariaStatus === 'fixing' && step.id === 'fix')
      status = isCurrentlyRunning ? 'running' : 'done'
    }

    result[step.id] = {
      status,
      durationMs: first && last ? last.getTime() - first.getTime() : null,
      errorExcerpt: errorEvent ? errorEvent.message.slice(0, 48) : null,
      firstSeen: first,
      lastSeen: last,
    }
  }
  return result
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}
