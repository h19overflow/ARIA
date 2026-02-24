import { useState } from 'react'
import { ChevronRight, ChevronDown } from 'lucide-react'
import clsx from 'clsx'
import type { ARIAState } from '@/types'

interface StateViewerProps {
  ariaState: ARIAState | null
}

interface SectionProps {
  label: string
  value: unknown
}

function JsonValue({ value }: { value: unknown }): React.ReactElement {
  if (value === null || value === undefined) {
    return <span className="text-[var(--text-muted)]">null</span>
  }
  if (typeof value === 'boolean') {
    return <span className="text-[var(--accent-violet)]">{String(value)}</span>
  }
  if (typeof value === 'number') {
    return <span className="text-[var(--color-success)]">{value}</span>
  }
  if (typeof value === 'string') {
    return <span className="text-[var(--color-warning)]">"{value}"</span>
  }
  return <span className="text-[var(--text-secondary)]">{JSON.stringify(value, null, 2)}</span>
}

function Section({ label, value }: SectionProps) {
  const [open, setOpen] = useState(false)
  const isComplex = typeof value === 'object' && value !== null

  return (
    <div className="border-b border-[var(--border-subtle)] last:border-0">
      <button
        onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center gap-2 px-4 py-2.5 hover:bg-white/[0.02] transition-colors duration-150 text-left"
      >
        {isComplex ? (
          open ? <ChevronDown size={12} className="text-[var(--text-muted)]" /> : <ChevronRight size={12} className="text-[var(--text-muted)]" />
        ) : (
          <span className="w-3" />
        )}
        <span className="text-xs font-mono text-[var(--accent-indigo)] font-medium">{label}</span>
        {!open && !isComplex && (
          <span className="ml-2 text-xs font-mono truncate max-w-xs">
            <JsonValue value={value} />
          </span>
        )}
        {!open && isComplex && (
          <span className="ml-2 text-[10px] text-[var(--text-muted)]">
            {Array.isArray(value) ? `[${(value as unknown[]).length}]` : '{…}'}
          </span>
        )}
      </button>
      {open && isComplex && (
        <pre className="px-8 pb-3 text-[11px] font-mono text-[var(--text-secondary)] leading-relaxed overflow-x-auto whitespace-pre-wrap break-words">
          {JSON.stringify(value, null, 2)}
        </pre>
      )}
    </div>
  )
}

export function StateViewer({ ariaState }: StateViewerProps) {
  if (!ariaState) {
    return (
      <div className="flex items-center justify-center h-32 text-[var(--text-muted)] text-sm">
        No state yet — submit a prompt to begin
      </div>
    )
  }

  const entries = Object.entries(ariaState).filter(([, v]) => v !== undefined)

  return (
    <div
      className={clsx(
        'glass rounded-xl overflow-hidden',
      )}
    >
      <div className="px-4 py-2.5 border-b border-[var(--border-subtle)]">
        <span className="text-xs font-semibold text-white">Raw State</span>
        <span className="ml-2 text-[10px] text-[var(--text-muted)]">{entries.length} keys</span>
      </div>
      {entries.map(([key, val]) => (
        <Section key={key} label={key} value={val} />
      ))}
    </div>
  )
}
