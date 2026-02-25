import clsx from 'clsx'
import { X, Link2, ExternalLink, Asterisk } from 'lucide-react'
import type { CredentialGuideEntry } from '@/types'

export function FieldInput({
  field,
  value,
  onChange,
}: {
  field: CredentialGuideEntry['fields'][number]
  value: string
  onChange: (v: string) => void
}) {
  const inputType = field.type === 'password' ? 'password' : 'text'

  return (
    <div className="flex flex-col gap-1.5">
      <label className="flex items-center gap-1 text-xs font-medium text-white/60">
        {field.label}
        {field.required && <Asterisk size={8} className="text-orange/60" />}
      </label>
      <input
        type={inputType}
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
      {field.description && (
        <span className="text-[11px] text-white/30 leading-snug">{field.description}</span>
      )}
    </div>
  )
}

export function CardHeader({ entry, onDismiss }: { entry: CredentialGuideEntry; onDismiss: () => void }) {
  return (
    <div className="flex items-start justify-between px-6 py-5 border-b border-white/8">
      <div className="flex items-start gap-3">
        <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-orange/12 border border-orange/25 mt-0.5">
          <Link2 size={16} className="text-orange" />
        </div>
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-white/90">{entry.display_name}</h2>
          <p className="text-xs text-white/35 mt-0.5 leading-snug">{entry.service_description}</p>
        </div>
      </div>
      <button
        onClick={onDismiss}
        className="flex items-center justify-center w-7 h-7 rounded-lg hover:bg-white/8 text-white/35 hover:text-white/70 transition-colors flex-shrink-0"
      >
        <X size={14} />
      </button>
    </div>
  )
}

export function CardBody({
  entry,
  values,
  onField,
}: {
  entry: CredentialGuideEntry
  values: Record<string, string>
  onField: (name: string, value: string) => void
}) {
  return (
    <div className="px-6 py-5 flex flex-col gap-4 max-h-[50vh] overflow-y-auto">
      {entry.how_to_obtain && (
        <div className="flex flex-col gap-2 rounded-lg bg-white/[0.03] border border-white/6 px-3.5 py-3">
          <p className="text-xs text-white/50 leading-relaxed">{entry.how_to_obtain}</p>
          {entry.help_url && (
            <a
              href={entry.help_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-[11px] font-medium text-orange/70 hover:text-orange transition-colors w-fit"
            >
              View setup guide <ExternalLink size={10} />
            </a>
          )}
        </div>
      )}

      {entry.fields.map((field) => (
        <FieldInput
          key={field.name}
          field={field}
          value={values[field.name] ?? ''}
          onChange={(v) => onField(field.name, v)}
        />
      ))}
    </div>
  )
}

export function CardFooter({
  canSubmit,
  onSubmit,
  onDismiss,
}: {
  canSubmit: boolean
  onSubmit: () => void
  onDismiss: () => void
}) {
  return (
    <div className="flex flex-col gap-2 px-6 pb-5 pt-1">
      <button
        onClick={onSubmit}
        disabled={!canSubmit}
        className={clsx(
          'w-full py-2.5 rounded-lg font-semibold text-sm text-white transition-all duration-150',
          canSubmit
            ? 'bg-orange hover:bg-orange/90 shadow-glow-orange hover:-translate-y-0.5'
            : 'bg-white/8 text-white/30 cursor-not-allowed',
        )}
      >
        Save Connection
      </button>
      <button
        onClick={onDismiss}
        className="text-center text-xs text-white/25 hover:text-white/45 transition-colors py-1"
      >
        Cancel
      </button>
    </div>
  )
}
