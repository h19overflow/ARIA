import { useState, useRef } from 'react'
import { Sparkles, RotateCcw, Loader2 } from 'lucide-react'
import clsx from 'clsx'

interface PromptInputProps {
  onSubmit: (prompt: string) => void
  onReset: () => void
  isLoading: boolean
}

export function PromptInput({ onSubmit, onReset, isLoading }: PromptInputProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function handleSubmit() {
    const trimmed = value.trim()
    if (!trimmed || isLoading) return
    onSubmit(trimmed)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit()
  }

  function handleReset() {
    setValue('')
    onReset()
    textareaRef.current?.focus()
  }

  const canSubmit = Boolean(value.trim()) && !isLoading

  return (
    <div
      className={clsx(
        'rounded-xl border transition-all duration-200',
        'bg-[var(--bg-elevated)]',
        isLoading
          ? 'border-[var(--accent-indigo)]/40'
          : 'border-[var(--border-muted)] focus-within:border-[var(--accent-indigo)]/50',
      )}
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={'Describe your automation in plain English…  e.g. "When a Typeform is submitted, save to Airtable and ping Slack"'}
        disabled={isLoading}
        rows={2}
        className={clsx(
          'w-full resize-none bg-transparent px-4 pt-3.5 pb-1 text-sm text-white',
          'placeholder:text-[var(--text-muted)] focus:outline-none leading-relaxed',
          isLoading && 'opacity-50 cursor-not-allowed',
        )}
      />
      <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
        <span className="text-[10px] text-[var(--text-muted)]">
          {value.length > 0 ? `${value.length} chars · ` : ''}
          <kbd className="font-mono">⌘ Enter</kbd> to build
        </span>
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleReset}
            disabled={!value && !isLoading}
            aria-label="Reset"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-[var(--text-muted)] hover:text-white hover:bg-white/5 transition-all duration-150 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <RotateCcw size={11} />
            Reset
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={clsx(
              'flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200',
              'bg-[var(--accent-indigo)] text-white shadow-md shadow-indigo-500/25',
              'hover:bg-indigo-500 active:scale-95',
              'disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none disabled:scale-100',
            )}
          >
            {isLoading ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Sparkles size={12} />
            )}
            {isLoading ? 'Building…' : 'Build'}
          </button>
        </div>
      </div>
    </div>
  )
}
