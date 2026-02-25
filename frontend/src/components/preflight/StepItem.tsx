import clsx from 'clsx'
import { Check, X, Loader } from 'lucide-react'

export type StepStatus = 'idle' | 'running' | 'done' | 'error'

interface StepItemProps {
  index: number
  label: string
  description: string
  status: StepStatus
  detail?: string
  isLast?: boolean
}

function StepIcon({ status, index }: { status: StepStatus; index: number }) {
  if (status === 'done') {
    return (
      <span className="flex items-center justify-center w-7 h-7 rounded-full bg-success/20 border border-success/40">
        <Check size={13} className="text-success" strokeWidth={2.5} />
      </span>
    )
  }
  if (status === 'running') {
    return (
      <span className="relative flex items-center justify-center w-7 h-7 rounded-full bg-orange/15 border border-orange/40">
        <Loader size={13} className="text-orange animate-spin-slow" />
        <span className="absolute inset-0 rounded-full animate-ping opacity-30 bg-orange" style={{ animationDuration: '1.8s' }} />
      </span>
    )
  }
  if (status === 'error') {
    return (
      <span className="flex items-center justify-center w-7 h-7 rounded-full bg-error/20 border border-error/40">
        <X size={13} className="text-error" strokeWidth={2.5} />
      </span>
    )
  }
  return (
    <span className="flex items-center justify-center w-7 h-7 rounded-full border border-white/10">
      <span className="text-[10px] font-mono font-bold text-white/30">{String(index + 1).padStart(2, '0')}</span>
    </span>
  )
}

export function StepItem({ index, label, description, status, detail, isLast }: StepItemProps) {
  return (
    <div className="flex gap-3">
      {/* Left: icon + connector */}
      <div className="flex flex-col items-center">
        <StepIcon status={status} index={index} />
        {!isLast && (
          <div
            className={clsx(
              'w-px flex-1 mt-1 min-h-[24px] transition-colors duration-700',
              status === 'done' ? 'bg-success/30' : 'bg-white/6',
            )}
          />
        )}
      </div>

      {/* Right: text */}
      <div className={clsx('pb-5 min-w-0', isLast && 'pb-0')}>
        <p
          className={clsx(
            'text-sm font-medium leading-tight transition-colors duration-300',
            status === 'done' && 'text-white/90',
            status === 'running' && 'text-orange',
            status === 'idle' && 'text-white/30',
            status === 'error' && 'text-error',
          )}
        >
          {label}
        </p>
        <p className="text-xs text-white/30 mt-0.5 leading-relaxed">
          {status === 'done' && detail ? detail : description}
        </p>
        {status === 'running' && (
          <div className="mt-2 h-0.5 w-full rounded-full bg-white/6 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-orange/60 via-orange to-orange/60"
              style={{
                width: '40%',
                animation: 'scanLine 1.4s ease-in-out infinite',
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}
