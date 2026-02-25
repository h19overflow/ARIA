import clsx from 'clsx'
import { Link2, Check, AlertCircle, Loader } from 'lucide-react'
import type { ARIAState } from '@/types'

interface CredentialChecklistProps {
  ariaState: ARIAState | null
  onConnect?: (credentialType: string) => void
}

function cleanLabel(raw: string): string {
  return raw
    .replace(/OAuth2?/gi, '')
    .replace(/API/gi, '')
    .replace(/credentials?/gi, '')
    .replace(/\s+/g, ' ')
    .trim()
}

type CredStatus = 'resolved' | 'pending' | 'missing'

interface CredRow {
  type: string
  label: string
  status: CredStatus
}

function buildRows(ariaState: ARIAState | null): CredRow[] {
  if (!ariaState) return []
  const resolved = ariaState.resolved_credential_ids ?? {}
  const pending = ariaState.pending_credential_types ?? []
  const required = ariaState.required_nodes ?? []

  const seen = new Set<string>()
  const rows: CredRow[] = []

  for (const type of Object.keys(resolved)) {
    if (seen.has(type)) continue
    seen.add(type)
    rows.push({ type, label: cleanLabel(type), status: 'resolved' })
  }
  for (const type of pending) {
    if (seen.has(type)) continue
    seen.add(type)
    rows.push({ type, label: cleanLabel(type), status: 'missing' })
  }
  for (const node of required) {
    if (seen.has(node)) continue
    seen.add(node)
    rows.push({ type: node, label: cleanLabel(node), status: 'pending' })
  }

  return rows
}

export function CredentialChecklist({ ariaState, onConnect }: CredentialChecklistProps) {
  const rows = buildRows(ariaState)

  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.02] p-4">
      <div className="flex items-center gap-2 mb-3">
        <Link2 size={14} className="text-white/40" />
        <span className="text-xs font-mono font-semibold text-white/40 uppercase tracking-widest">Connections</span>
      </div>

      {rows.length === 0 ? (
        <div className="flex items-center gap-2 py-1">
          <Loader size={12} className="text-white/20 animate-spin-slow" />
          <span className="text-sm text-white/25 font-mono">Checking...</span>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {rows.map((row) => (
            <div key={row.type} className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className={clsx(
                    'flex-shrink-0 flex items-center justify-center w-5 h-5 rounded-full',
                    row.status === 'resolved' && 'bg-success/20',
                    row.status === 'missing' && 'bg-error/20',
                    row.status === 'pending' && 'bg-white/8',
                  )}
                >
                  {row.status === 'resolved' && <Check size={10} className="text-success" strokeWidth={3} />}
                  {row.status === 'missing' && <AlertCircle size={10} className="text-error" />}
                  {row.status === 'pending' && <span className="w-1.5 h-1.5 rounded-full bg-white/20" />}
                </span>
                <span
                  className={clsx(
                    'text-sm truncate',
                    row.status === 'resolved' && 'text-white/70',
                    row.status === 'missing' && 'text-error/80',
                    row.status === 'pending' && 'text-white/30',
                  )}
                >
                  {row.label}
                </span>
              </div>

              {row.status === 'missing' && onConnect && (
                <button
                  onClick={() => onConnect(row.type)}
                  className="flex-shrink-0 text-[11px] font-semibold text-orange hover:text-orange/80 transition-colors"
                >
                  Connect →
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
