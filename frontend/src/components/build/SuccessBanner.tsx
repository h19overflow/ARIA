import { ExternalLink } from 'lucide-react'
import clsx from 'clsx'

interface SuccessBannerProps {
  n8nWorkflowUrl: string | undefined
}

export function SuccessBanner({ n8nWorkflowUrl }: SuccessBannerProps) {
  return (
    <div className="absolute inset-x-0 bottom-0 z-30 animate-slide-up">
      <div className={clsx(
        'mx-4 mb-4 rounded-xl overflow-hidden',
        'border border-[var(--phase-2)]/30',
        'bg-gradient-to-r from-emerald-950/90 via-[#0d2b1f]/95 to-emerald-950/90',
        'backdrop-blur-md shadow-[0_8px_40px_rgba(16,185,129,0.2)]',
      )}>
        <div className="h-px bg-gradient-to-r from-transparent via-[var(--phase-2)] to-transparent" />

        <div className="p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[var(--phase-2)]/15 flex items-center justify-center flex-none text-lg">
              🎉
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Workflow created!</p>
              <p className="text-xs text-[var(--text-muted)]">
                Deployed as inactive draft in n8n
              </p>
            </div>
          </div>

          {n8nWorkflowUrl && (
            <a
              href={n8nWorkflowUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium',
                'bg-[var(--phase-2)]/15 text-[var(--phase-2)] border border-[var(--phase-2)]/25',
                'hover:bg-[var(--phase-2)]/25 transition-all duration-150',
              )}
            >
              <ExternalLink size={11} />
              Open in n8n
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
