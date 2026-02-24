import { useState, useEffect, useRef } from 'react';
import { Check, X, Edit2 } from 'lucide-react';
import { clsx } from 'clsx';

interface NoteFieldProps {
  label: string;
  noteKey: string;
  value?: string | null;
  onUpdate: (key: string, value: string | null) => void;
}

export function NoteField({ label, noteKey, value, onUpdate }: NoteFieldProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(value ?? '');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setDraft(value ?? '');
  }, [value]);

  useEffect(() => {
    if (isEditing) inputRef.current?.focus();
  }, [isEditing]);

  const commitSave = () => {
    onUpdate(noteKey, draft.trim() || null);
    setIsEditing(false);
  };

  const commitCancel = () => {
    setDraft(value ?? '');
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') commitSave();
    if (e.key === 'Escape') commitCancel();
  };

  return (
    <div className="note-field" style={{ animation: value ? 'noteFadeIn 150ms ease' : 'none' }}>
      <span
        style={{
          display: 'block',
          fontSize: '0.625rem',
          fontWeight: 600,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: 'var(--text-muted)',
          marginBottom: '4px',
          fontFamily: 'monospace',
        }}
      >
        {label}
      </span>

      {isEditing ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={commitSave}
            style={{
              flex: 1,
              background: 'var(--bg-base)',
              border: '1px solid var(--accent-indigo)',
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: '0.8rem',
              color: 'var(--text-primary)',
              fontFamily: 'monospace',
              outline: 'none',
            }}
          />
          <button onClick={commitSave} style={{ color: 'var(--color-success)', lineHeight: 0 }}>
            <Check size={13} />
          </button>
          <button onClick={commitCancel} style={{ color: 'var(--text-muted)', lineHeight: 0 }}>
            <X size={13} />
          </button>
        </div>
      ) : (
        <div
          onClick={() => setIsEditing(true)}
          className={clsx('note-field-display', !value && 'note-field-empty')}
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '5px 8px',
            borderRadius: '4px',
            border: value ? '1px solid var(--border-subtle)' : '1px dashed var(--border-muted)',
            background: value ? 'var(--bg-base)' : 'transparent',
            cursor: 'text',
            transition: 'border-color 150ms ease',
            fontSize: '0.8rem',
            fontFamily: 'monospace',
            color: value ? 'var(--text-primary)' : 'var(--text-muted)',
          }}
        >
          <span style={{ fontStyle: value ? 'normal' : 'italic' }}>{value ?? 'Pending...'}</span>
          <Edit2 size={11} style={{ opacity: 0, color: 'var(--text-muted)', flexShrink: 0 }} className="note-edit-icon" />
        </div>
      )}
    </div>
  );
}
