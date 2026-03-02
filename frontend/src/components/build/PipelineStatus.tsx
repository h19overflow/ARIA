import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'
import clsx from 'clsx'
import type { WorkflowStatus } from '@/types'

interface Stage {
  id: string
  label: string
  statuses: WorkflowStatus[]
}

interface PipelineStatusProps {
  status: WorkflowStatus
  buildPhase?: number
  totalPhases?: number
}

const STAGES: Stage[] = [
  { id: 'preflight', label: 'Preflight', statuses: ['planning'] },
  { id: 'build', label: 'Build', statuses: ['building'] },
  { id: 'done', label: 'Done', statuses: ['done'] },
]

const STATUS_ORDER = ['planning', 'building', 'done', 'failed']

function getStageState(
  stage: Stage,
  current: WorkflowStatus,
): 'idle' | 'active' | 'done' | 'error' {
  if (current === 'failed') {
    const currentIdx = STATUS_ORDER.indexOf(current)
    const stageIdx = Math.min(...stage.statuses.map((s) => STATUS_ORDER.indexOf(s)))
    return stageIdx < currentIdx ? 'done' : stageIdx === currentIdx ? 'error' : 'idle'
  }
  if (stage.statuses.includes(current)) return 'active'
  const currentIdx = STATUS_ORDER.indexOf(current)
  const stageIdx = Math.min(...stage.statuses.map((s) => STATUS_ORDER.indexOf(s)))
  return stageIdx < currentIdx ? 'done' : 'idle'
}

function StageIcon({ state }: { state: ReturnType<typeof getStageState> }) {
  if (state === 'done') return <CheckCircle2 size={14} className="text-[var(--color-success)]" />
  if (state === 'error') return <XCircle size={14} className="text-[var(--color-error)]" />
  if (state === 'active') return <Loader2 size={14} className="text-[var(--accent-indigo)] animate-spin" />
  return <Circle size={14} className="text-[var(--text-muted)]" />
}

export function PipelineStatus({ status, buildPhase, totalPhases }: PipelineStatusProps) {
  if (status === 'idle') return null

  return (
    <div className="flex items-center gap-1 px-4 py-2 glass rounded-xl">
      {STAGES.map((stage, i) => {
        const state = getStageState(stage, status)
        return (
          <div key={stage.id} className="flex items-center gap-1">
            <div className="flex items-center gap-1.5">
              <StageIcon state={state} />
              <span
                className={clsx('text-xs font-medium transition-colors duration-200', {
                  'text-white': state === 'active',
                  'text-[var(--color-success)]': state === 'done',
                  'text-[var(--color-error)]': state === 'error',
                  'text-[var(--text-muted)]': state === 'idle',
                })}
              >
                {stage.label}
                {state === 'active' && stage.id === 'build' && buildPhase && totalPhases
                  ? ` ${buildPhase}/${totalPhases}`
                  : ''}
              </span>
            </div>
            {i < STAGES.length - 1 && (
              <div
                className={clsx('w-8 h-px mx-1 transition-colors duration-200', {
                  'bg-[var(--color-success)]': state === 'done',
                  'bg-[var(--border-subtle)]': state !== 'done',
                })}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
