import { useState } from 'react'
import type { CredentialGuideEntry } from '@/types'
import { CardHeader, CardBody, CardFooter } from './CredentialCardParts'

interface CredentialCardProps {
  entry: CredentialGuideEntry
  onSubmit: (credentials: Record<string, string>) => void
  onDismiss: () => void
}

export function CredentialCard({ entry, onSubmit, onDismiss }: CredentialCardProps) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(entry.fields.map((f) => [f.name, ''])),
  )

  const requiredFilled = entry.fields
    .filter((f) => f.required)
    .every((f) => (values[f.name] ?? '').trim().length > 0)

  function handleSubmit() {
    onSubmit(values)
  }

  function handleField(name: string, value: string) {
    setValues((prev) => ({ ...prev, [name]: value }))
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm animate-fade-in" onClick={onDismiss} />

      <div className="relative z-10 w-full max-w-md animate-slide-up">
        <div className="rounded-2xl border border-white/12 bg-[var(--bg-surface)] shadow-lg overflow-hidden">
          <CardHeader entry={entry} onDismiss={onDismiss} />
          <CardBody entry={entry} values={values} onField={handleField} />
          <CardFooter canSubmit={requiredFilled} onSubmit={handleSubmit} onDismiss={onDismiss} />
        </div>
      </div>
    </div>
  )
}
