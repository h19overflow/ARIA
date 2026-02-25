import { useEffect, useRef, useState } from 'react';
import { X, FileText } from 'lucide-react';
import type { ConversationNotes } from '@/store';
import { NoteField } from './NoteField';

interface ScratchpadPanelProps {
  notes: ConversationNotes;
  onUpdate: (key: string, value: string | null) => void;
}

function PulseIndicator({ active }: { active: boolean }) {
  return (
    <span
      style={{
        display: 'inline-block',
        width: '7px',
        height: '7px',
        borderRadius: '50%',
        background: active ? 'var(--color-success)' : 'var(--border-muted)',
        boxShadow: active ? '0 0 6px var(--color-success)' : 'none',
        animation: active ? 'pulse 1.2s ease-in-out infinite' : 'none',
        transition: 'background 300ms ease, box-shadow 300ms ease',
        flexShrink: 0,
      }}
    />
  );
}

function removeAt<T>(arr: T[], idx: number): T[] {
  return arr.filter((_, i) => i !== idx);
}

export function ScratchpadPanel({ notes, onUpdate }: ScratchpadPanelProps) {
  const [isActive, setIsActive] = useState(false);
  const notesRef = useRef(notes);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (notesRef.current !== notes) {
      notesRef.current = notes;
      setIsActive(true);
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setIsActive(false), 2000);
    }
  }, [notes]);

  const removeConstraint = (idx: number) => {
    const updated = removeAt(notes.constraints ?? [], idx);
    onUpdate('constraints', updated.join('||'));
  };

  const removeIntegration = (idx: number) => {
    const updated = removeAt(notes.required_integrations ?? [], idx);
    onUpdate('required_integrations', updated.join('||'));
  };

  return (
    <div
      style={{
        width: '280px',
        flexShrink: 0,
        background: 'var(--bg-surface)',
        borderLeft: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <FileText size={13} style={{ color: 'var(--text-muted)' }} />
        <span style={{ fontSize: '0.75rem', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-secondary)', flex: 1 }}>
          Scratchpad
        </span>
        <PulseIndicator active={isActive} />
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <NoteField label="Summary" noteKey="summary" value={notes.summary} onUpdate={onUpdate} />
        <NoteField label="Trigger" noteKey="trigger" value={notes.trigger} onUpdate={onUpdate} />
        <NoteField label="Destination" noteKey="destination" value={notes.destination} onUpdate={onUpdate} />
        <NoteField label="Data Transform" noteKey="data_transform" value={notes.data_transform} onUpdate={onUpdate} />

        {/* Constraints */}
        <div>
          <span style={{ display: 'block', fontSize: '0.625rem', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '6px', fontFamily: 'monospace' }}>
            Constraints
          </span>
          {(notes.constraints ?? []).length === 0 ? (
            <div style={{ border: '1px dashed var(--border-muted)', borderRadius: '4px', padding: '5px 8px', fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic', fontFamily: 'monospace' }}>
              Pending...
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {notes.constraints!.map((c, i) => (
                <div
                  key={i}
                  className="scratchpad-list-item"
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '5px 8px', fontSize: '0.75rem', color: 'var(--text-primary)', fontFamily: 'monospace', gap: '6px' }}
                >
                  <span style={{ flex: 1 }}>{c}</span>
                  <button onClick={() => removeConstraint(i)} style={{ color: 'var(--text-muted)', lineHeight: 0, flexShrink: 0, transition: 'color 150ms ease' }} className="scratchpad-remove-btn">
                    <X size={11} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Integrations */}
        <div>
          <span style={{ display: 'block', fontSize: '0.625rem', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '6px', fontFamily: 'monospace' }}>
            Integrations
          </span>
          {(notes.required_integrations ?? []).length === 0 ? (
            <div style={{ border: '1px dashed var(--border-muted)', borderRadius: '4px', padding: '5px 8px', fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic', fontFamily: 'monospace' }}>
              Pending...
            </div>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {notes.required_integrations!.map((integ, i) => (
                <span
                  key={i}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '3px 8px', background: 'rgba(238,79,39,0.10)', border: '1px solid rgba(238,79,39,0.22)', borderRadius: '99px', fontSize: '0.7rem', fontWeight: 500, color: 'var(--accent-orange)', fontFamily: 'monospace' }}
                >
                  {integ}
                  <button onClick={() => removeIntegration(i)} style={{ lineHeight: 0, color: 'var(--accent-orange)', opacity: 0.6, transition: 'opacity 150ms ease' }}>
                    <X size={10} />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
