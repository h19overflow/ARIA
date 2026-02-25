import { useState } from 'react'
import clsx from 'clsx'
import { HelpCircle, X, ChevronRight } from 'lucide-react'

export interface GuideStep {
  label: string
  detail: string
}

interface PageGuideProps {
  title: string
  steps: GuideStep[]
  storageKey: string
}

export function PageGuide({ title, steps, storageKey }: PageGuideProps) {
  const [dismissed, setDismissed] = useState(() => {
    try { return sessionStorage.getItem(storageKey) === '1' } catch { return false }
  })
  const [expanded, setExpanded] = useState(false)

  if (dismissed) return null

  function handleDismiss() {
    setDismissed(true)
    try { sessionStorage.setItem(storageKey, '1') } catch { /* noop */ }
  }

  return (
    <div className={clsx(
      'animate-fade-in rounded-xl border transition-all duration-300',
      'bg-white/[0.02] border-white/8',
    )}>
      {/* Collapsed bar */}
      <div className="flex items-center gap-2.5 px-3.5 py-2.5">
        <HelpCircle size={13} className="text-orange flex-shrink-0" />
        <button
          onClick={() => setExpanded((p) => !p)}
          className="flex-1 flex items-center gap-1.5 text-left group"
        >
          <span className="text-xs font-medium text-white/60 group-hover:text-white/80 transition-colors">
            {title}
          </span>
          <ChevronRight
            size={11}
            className={clsx(
              'text-white/30 transition-transform duration-200',
              expanded && 'rotate-90',
            )}
          />
        </button>
        <button
          onClick={handleDismiss}
          className="text-white/20 hover:text-white/50 transition-colors flex-shrink-0"
          aria-label="Dismiss guide"
        >
          <X size={12} />
        </button>
      </div>

      {/* Expanded steps */}
      {expanded && (
        <div className="px-3.5 pb-3 pt-0 animate-fade-in">
          <ol className="flex flex-col gap-2">
            {steps.map((step, i) => (
              <li key={i} className="flex gap-2.5">
                <span className="flex-shrink-0 w-4 h-4 rounded-full bg-orange/10 border border-orange/20 flex items-center justify-center mt-0.5">
                  <span className="text-[9px] font-mono font-bold text-orange">{i + 1}</span>
                </span>
                <div className="min-w-0">
                  <p className="text-[11px] font-medium text-white/70 leading-tight">{step.label}</p>
                  <p className="text-[10px] text-white/35 leading-relaxed mt-0.5">{step.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}
