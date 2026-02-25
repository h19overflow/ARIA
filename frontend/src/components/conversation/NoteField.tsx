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

  useEffect(() => { setDraft(value ?? ''); }, [value]);
  useEffect(() => { if (isEditing) inputRef.current?.focus(); }, [isEditing]);

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
    <div>
      <span style={{
        display: 'block', fontSize: '0.65rem', fontWeight: 600,
        letterSpacing: '0.04em', color: 'var(--accent-indigo)',
        marginBottom: '5px', opacity: 0.85,
      }}>
        {label}
      </span>

      {isEditing ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <input
            ref={inputRef}
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={commitSave}
            style={{
              flex: 1, background: 'var(--bg-base)',
              border: '1px solid var(--accent-indigo)',
              borderRadius: '6px', padding: '5px 8px',
              fontSize: '0.8rem', color: 'var(--text-primary)',
              outline: 'none',
            }}
          />
          <button onClick={commitSave} style={{ color: 'var(--color-success)', lineHeight: 0 }}><Check size={13} /></button>
          <button onClick={commitCancel} style={{ color: 'var(--text-muted)', lineHeight: 0 }}><X size={13} /></button>
        </div>
      ) : (
        <div
          onClick={() => setIsEditing(true)}
          className={clsx('note-field-display', 'group')}
          style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
            cursor: 'text', gap: '6px',
          }}
        >
          <span style={{
            fontSize: '0.8rem', lineHeight: 1.5, flex: 1,
            color: value ? 'var(--text-primary)' : 'var(--text-muted)',
            fontStyle: value ? 'normal' : 'italic',
          }}>
            {value ?? 'Not yet captured...'}
          </span>
          <Edit2
            size={11}
            style={{ opacity: 0, color: 'var(--text-muted)', flexShrink: 0, marginTop: '2px' }}
            className="note-edit-icon"
          />
        </div>
      )}
    </div>
  );
}
