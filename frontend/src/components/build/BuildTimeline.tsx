import clsx from 'clsx'
import {
  Search, Cpu, Rocket,
  CheckCircle2, XCircle, Loader2, Circle,
} from 'lucide-react'
import type { WorkflowStatus, FeedEvent } from '@/types'
import { BUILD_STEPS, deriveStepStates, formatDuration } from './buildTimelineUtils'
import type { Step, StepState } from './buildTimelineUtils'

const STEP_ICONS: Record<string, React.ReactNode> = {
  rag:      <Search size={13} />,
  engineer: <Cpu size={13} />,
  deploy:   <Rocket size={13} />,
}

interface TimelineStepProps {
  step: Step
  stepState: StepState
  isLast: boolean
}

function TimelineStep({ step, stepState, isLast }: TimelineStepProps) {
  const { status, durationMs, errorExcerpt } = stepState

  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className={clsx(
          'w-7 h-7 rounded-full flex items-center justify-center flex-none transition-all duration-300',
          status === 'pending' && 'bg-white/5 text-[var(--text-muted)]',
          status === 'running' && 'bg-[var(--phase-2-dim)] text-[var(--phase-2)] animate-glow-pulse',
          status === 'done'    && 'bg-[var(--phase-2-dim)] text-[var(--phase-2)]',
          status === 'error'   && 'bg-red-500/10 text-[var(--color-error)]',
        )}>
          {status === 'running' && <Loader2 size={13} className="animate-spin" />}
          {status === 'done'    && <CheckCircle2 size={13} />}
          {status === 'error'   && <XCircle size={13} />}
          {status === 'pending' && <Circle size={13} />}
        </div>
        {!isLast && (
          <div className={clsx(
            'w-px flex-1 mt-1 min-h-4',
            status === 'done' ? 'bg-[var(--phase-2)]/30' : 'bg-white/6',
          )} />
        )}
      </div>
      <div className="pb-4 flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className={clsx(
              'text-xs font-medium',
              status === 'pending' && 'text-[var(--text-muted)]',
              status === 'running' && 'text-[var(--phase-2)]',
              status === 'done'    && 'text-[var(--text-secondary)]',
              status === 'error'   && 'text-[var(--color-error)]',
            )}>
              {step.label}
            </span>
          </div>
          {durationMs !== null && (
            <span className="text-[10px] text-[var(--text-muted)] tabular-nums flex-none">
              {formatDuration(durationMs)}
            </span>
          )}
        </div>
        {errorExcerpt && (
          <p className="mt-0.5 text-[10px] text-[var(--color-error)]/70 leading-relaxed truncate">
            {errorExcerpt}
          </p>
        )}
      </div>
    </div>
  )
}

interface BuildTimelineProps {
  status: WorkflowStatus
  events: FeedEvent[]
}

export function BuildTimeline({ status, events }: BuildTimelineProps) {
  const stepStates = deriveStepStates(status, events)

  return (
    <div className="px-3 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)] mb-3 px-1">
        Build Steps
      </p>
      {BUILD_STEPS.map((step, i) => (
        <TimelineStep
          key={step.id}
          step={{ ...step, icon: STEP_ICONS[step.id] }}
          stepState={stepStates[step.id] ?? { status: 'pending', durationMs: null, errorExcerpt: null, firstSeen: null, lastSeen: null }}
          isLast={i === BUILD_STEPS.length - 1}
        />
      ))}
    </div>
  )
}
