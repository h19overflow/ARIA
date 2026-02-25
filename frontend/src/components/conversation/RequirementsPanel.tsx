import { useEffect, useRef, useState } from 'react';
import { X, ArrowRight, Loader2, CheckCircle2 } from 'lucide-react';
import { clsx } from 'clsx';
import type { ConversationNotes } from '@/hooks/useConversation';
import { NoteField } from './NoteField';

interface RequirementsPanelProps {
  notes: ConversationNotes;
  isStreaming: boolean;
  isCommitted: boolean;
  isStarting?: boolean;
  onUpdate: (key: string, value: string | null) => void;
  onStartPreflight: () => void;
}

const FIELDS: { key: keyof ConversationNotes; label: string; friendly: string }[] = [
  { key: 'summary',        label: 'Summary',        friendly: "What's the goal?" },
  { key: 'trigger',        label: 'What starts it?', friendly: 'What starts it?' },
  { key: 'destination',    label: 'Where does it go?', friendly: 'Where does it go?' },
  { key: 'data_transform', label: 'How to transform?', friendly: 'How to transform?' },
];

function LiveDot({ active }: { active: boolean }) {
  return (
    <span className={clsx(
      'inline-block w-2 h-2 rounded-full flex-shrink-0 transition-all duration-300',
      active ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)] animate-pulse-dot' : 'bg-transparent'
    )} />
  );
}

function removeAt<T>(arr: T[], idx: number): T[] {
  return arr.filter((_, i) => i !== idx);
}

export function RequirementsPanel({
  notes, isStreaming, isCommitted, isStarting, onUpdate, onStartPreflight,
}: RequirementsPanelProps) {
  const [updatedKey, setUpdatedKey] = useState<string | null>(null);
  const notesRef = useRef(notes);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (notesRef.current === notes) return;
    // detect which key changed
    const prev = notesRef.current;
    notesRef.current = notes;
    for (const f of FIELDS) {
      if (prev[f.key] !== notes[f.key]) { flashKey(f.key); return; }
    }
    if (prev.constraints !== notes.constraints) { flashKey('constraints'); return; }
    if (prev.required_integrations !== notes.required_integrations) { flashKey('integrations'); }
  }, [notes]);

  function flashKey(key: string) {
    setUpdatedKey(key);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setUpdatedKey(null), 800);
  }

  const removeConstraint = (idx: number) => {
    const updated = removeAt(notes.constraints ?? [], idx);
    onUpdate('constraints', updated.join('||'));
  };

  const removeIntegration = (idx: number) => {
    const updated = removeAt(notes.required_integrations ?? [], idx);
    onUpdate('required_integrations', updated.join('||'));
  };

  const filledCount = FIELDS.filter(f => notes[f.key]).length;

  return (
    <aside style={{
      width: '300px', flexShrink: 0,
      background: 'var(--bg-surface)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 16px 12px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex', alignItems: 'center', gap: '8px',
      }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-secondary)', flex: 1 }}>
          Requirements
        </span>
        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
          {filledCount}/{FIELDS.length}
        </span>
        <LiveDot active={isStreaming} />
      </div>

      {/* Fields */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {FIELDS.map(f => (
          <div
            key={f.key}
            className={clsx('req-field-card', updatedKey === f.key && 'req-field-just-updated')}
            style={{ borderRadius: '8px', padding: '10px 12px', border: notes[f.key] ? '1px solid rgba(255,255,255,0.1)' : '1px dashed rgba(255,255,255,0.07)', background: notes[f.key] ? 'rgba(255,255,255,0.04)' : 'transparent', transition: 'border-color 300ms ease, background 300ms ease' }}
          >
            <NoteField
              label={f.friendly}
              noteKey={f.key}
              value={notes[f.key] as string | null | undefined}
              onUpdate={onUpdate}
            />
          </div>
        ))}

        {/* Integrations */}
        <div className={clsx('req-field-card', updatedKey === 'integrations' && 'req-field-just-updated')}
          style={{ borderRadius: '8px', padding: '10px 12px', border: '1px solid var(--border-subtle)', background: 'transparent' }}>
          <span style={{ display: 'block', fontSize: '0.6rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '7px' }}>
            Integrations
          </span>
          {(notes.required_integrations ?? []).length === 0 ? (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>Not yet captured...</span>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
              {notes.required_integrations!.map((integ, i) => (
                <span key={i} className="integration-chip">
                  {integ}
                  <button onClick={() => removeIntegration(i)} style={{ lineHeight: 0, color: 'var(--text-muted)', opacity: 0.6 }}><X size={10} /></button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Constraints */}
        <div className={clsx('req-field-card', updatedKey === 'constraints' && 'req-field-just-updated')}
          style={{ borderRadius: '8px', padding: '10px 12px', border: '1px solid var(--border-subtle)', background: 'transparent' }}>
          <span style={{ display: 'block', fontSize: '0.6rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '7px' }}>
            Constraints
          </span>
          {(notes.constraints ?? []).length === 0 ? (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>Not yet captured...</span>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {notes.constraints!.map((c, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', fontSize: '0.75rem', color: 'var(--text-primary)' }}>
                  <span style={{ flex: 1, lineHeight: 1.5 }}>{c}</span>
                  <button onClick={() => removeConstraint(i)} style={{ color: 'var(--text-muted)', lineHeight: 0, flexShrink: 0, transition: 'color 150ms ease' }}
                    onMouseEnter={e => (e.currentTarget.style.color = 'var(--color-error)')}
                    onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>
                    <X size={11} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Run Preflight CTA */}
      {isCommitted && (
        <div style={{ padding: '12px 14px 16px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
            <CheckCircle2 size={13} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
            <span style={{ fontSize: '0.72rem', color: 'var(--color-success)', fontWeight: 500 }}>Requirements captured</span>
          </div>
          <button
            className="btn-run-preflight"
            onClick={onStartPreflight}
            disabled={isStarting}
          >
            {isStarting
              ? <><Loader2 size={15} className="animate-spin" /> Starting preflight...</>
              : <>Run Preflight <ArrowRight size={15} /></>
            }
          </button>
        </div>
      )}
    </aside>
  );
}
