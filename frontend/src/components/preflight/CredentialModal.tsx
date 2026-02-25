import { useState } from 'react'
import clsx from 'clsx'
import { X, Link2 } from 'lucide-react'
import type { CredentialGuidePayload, CredentialField } from '@/types'

interface CredentialModalProps {
  interrupt: { kind: string; payload: Record<string, unknown> } | null
  onSubmit: (credentials: Record<string, unknown>) => void
  onDismiss: () => void
}

function cleanLabel(raw: string): string {
  return raw.replace(/OAuth2?/gi, '').replace(/API/gi, '').replace(/\s+/g, ' ').trim()
}

function CredentialFieldInput({
  field,
  value,
  onChange,
}: {
  field: CredentialField
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-white/60">{field.label}</label>
      <input
        type={field.type === 'password' ? 'password' : 'text'}
        placeholder={field.placeholder ?? ''}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={clsx(
          'w-full px-3 py-2.5 rounded-lg text-sm bg-white/[0.04] border border-white/12',
          'text-white/90 placeholder:text-white/25',
          'focus:outline-none focus:border-orange/50 focus:bg-white/[0.06]',
          'transition-colors duration-150',
        )}
      />
    </div>
  )
}

export function CredentialModal({ interrupt, onSubmit, onDismiss }: CredentialModalProps) {
  const guide = interrupt?.payload?.guide as CredentialGuidePayload | undefined
  const pendingTypes = (interrupt?.payload?.pending_types as string[] | undefined) ?? []
  const credentialType = guide?.credential_type ?? pendingTypes[0] ?? 'Connection'
  const fields: CredentialField[] = guide?.fields ?? []

  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(fields.map((f) => [f.name, ''])),
  )

  if (!interrupt || interrupt.kind !== 'credential') return null

  function handleSubmit() {
    onSubmit(values)
  }

  function handleField(name: string, value: string) {
    setValues((prev) => ({ ...prev, [name]: value }))
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm animate-fade-in"
        onClick={onDismiss}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-md animate-slide-up">
        <div className="rounded-2xl border border-white/12 bg-[var(--bg-surface)] shadow-lg overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-5 border-b border-white/8">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-orange/15 border border-orange/30">
                <Link2 size={15} className="text-orange" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-white/90">Connect your apps</h2>
                <p className="text-xs text-white/35 mt-0.5">{cleanLabel(credentialType)}</p>
              </div>
            </div>
            <button
              onClick={onDismiss}
              className="flex items-center justify-center w-7 h-7 rounded-lg hover:bg-white/8 text-white/35 hover:text-white/70 transition-colors"
            >
              <X size={14} />
            </button>
          </div>

          {/* Body */}
          <div className="px-6 py-5 flex flex-col gap-4">
            {guide?.instructions && (
              <p className="text-sm text-white/50 leading-relaxed bg-white/[0.03] rounded-lg px-3 py-2.5 border border-white/6">
                {guide.instructions}
              </p>
            )}

            {fields.length > 0 ? (
              fields.map((field) => (
                <CredentialFieldInput
                  key={field.name}
                  field={field}
                  value={values[field.name] ?? ''}
                  onChange={(v) => handleField(field.name, v)}
                />
              ))
            ) : (
              <p className="text-sm text-white/40">
                You'll need to connect <strong className="text-white/70">{cleanLabel(credentialType)}</strong> to continue.
              </p>
            )}
          </div>

          {/* Footer */}
          <div className="flex flex-col gap-2 px-6 pb-5">
            <button
              onClick={handleSubmit}
              className={clsx(
                'w-full py-2.5 rounded-lg font-semibold text-sm text-white',
                'bg-orange hover:bg-orange/90 transition-all duration-150',
                'shadow-glow-orange hover:-translate-y-0.5',
              )}
            >
              Save Connection
            </button>
            <button
              onClick={onDismiss}
              className="text-center text-xs text-white/25 hover:text-white/45 transition-colors py-1"
            >
              I'll connect later
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
