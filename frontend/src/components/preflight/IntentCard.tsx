import clsx from 'clsx'
import { Sparkles } from 'lucide-react'
import type { ARIAState } from '@/types'

interface IntentCardProps {
  ariaState: ARIAState | null
}

export function IntentCard({ ariaState }: IntentCardProps) {
  const intent = ariaState?.intent ?? ariaState?.intent_summary
  const isLoading = !intent

  return (
    <div className="phase-1-tint border border-phase1/20 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles size={14} className="text-phase1" />
        <span className="text-xs font-mono font-semibold text-phase1 uppercase tracking-widest">
          What we're building
        </span>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <div className="skeleton h-6 w-3/4 rounded-lg" />
          <div className="skeleton h-4 w-1/2 rounded-lg" />
        </div>
      ) : (
        <p
          className={clsx(
            'text-lg font-semibold text-white/90 leading-snug animate-slide-up',
          )}
        >
          {intent}
        </p>
      )}

      {ariaState?.intent_summary && ariaState.intent && (
        <p className="mt-2 text-sm text-white/45 leading-relaxed animate-fade-in">
          {ariaState.intent_summary}
        </p>
      )}
    </div>
  )
}
