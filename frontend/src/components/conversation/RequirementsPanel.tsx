import { useEffect, useRef, useState } from 'react';
import { clsx } from 'clsx';
import type { ConversationNotes } from '@/store';
import { NoteField } from './NoteField';
import { CredentialStatusCard, getAllCredentialTypes } from './CredentialStatusCard';
import { IntegrationsList } from './IntegrationsList';
import { ConstraintsList } from './ConstraintsList';
import { StartBuildCta } from './StartBuildCta';

interface RequirementsPanelProps {
  notes: ConversationNotes;
  isStreaming: boolean;
  isCommitted: boolean;
  isStarting?: boolean;
  isDiscoveringCredentials?: boolean;
  onUpdate: (key: string, value: string | null) => void;
  onStartBuild: () => void;
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
  notes, isStreaming, isCommitted, isStarting, isDiscoveringCredentials, onUpdate, onStartBuild,
}: RequirementsPanelProps) {
  const [updatedKey, setUpdatedKey] = useState<string | null>(null);
  const notesRef = useRef(notes);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (notesRef.current === notes) return;
    const prev = notesRef.current;
    notesRef.current = notes;
    for (const f of FIELDS) {
      if (prev[f.key] !== notes[f.key]) { flashKey(f.key); return; }
    }
    if (prev.constraints !== notes.constraints) { flashKey('constraints'); return; }
    if (prev.required_integrations !== notes.required_integrations) { flashKey('integrations'); return; }
    if (prev.trigger_type !== notes.trigger_type || prev.trigger_service !== notes.trigger_service
      || prev.trigger_schedule !== notes.trigger_schedule) { flashKey('trigger'); return; }
    if (prev.destination_service !== notes.destination_service
      || prev.destination_action !== notes.destination_action) { flashKey('destination'); return; }
    if (prev.transform !== notes.transform) { flashKey('data_transform'); }
  }, [notes]);

  function flashKey(key: string) {
    setUpdatedKey(key);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setUpdatedKey(null), 800);
  }

  const removeConstraint = (idx: number) => onUpdate('constraints', removeAt(notes.constraints ?? [], idx).join('||'));
  const removeIntegration = (idx: number) => onUpdate('required_integrations', removeAt(notes.required_integrations ?? [], idx).join('||'));

  const filledCount = FIELDS.filter(f => notes[f.key]).length;
  const allCredentialTypes = getAllCredentialTypes(notes);
  const canStartBuild = isCommitted && notes.credentials_committed;

  return (
    <aside style={{
      width: '300px', flexShrink: 0, background: 'var(--bg-surface)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      <div style={{ padding: '14px 16px 12px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-secondary)', flex: 1 }}>
          Requirements
        </span>
        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{filledCount}/{FIELDS.length}</span>
        <LiveDot active={isStreaming} />
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {FIELDS.map(f => (
          <div key={f.key} className={clsx('req-field-card', updatedKey === f.key && 'req-field-just-updated')}
            style={{ borderRadius: '8px', padding: '10px 12px', border: notes[f.key] ? '1px solid rgba(255,255,255,0.1)' : '1px dashed rgba(255,255,255,0.07)', background: notes[f.key] ? 'rgba(255,255,255,0.04)' : 'transparent', transition: 'border-color 300ms ease, background 300ms ease' }}>
            <NoteField label={f.friendly} noteKey={f.key} value={notes[f.key] as string | null | undefined} onUpdate={onUpdate} />
          </div>
        ))}
        <IntegrationsList integrations={notes.required_integrations ?? []} isHighlighted={updatedKey === 'integrations'} onRemove={removeIntegration} />
        <ConstraintsList constraints={notes.constraints ?? []} isHighlighted={updatedKey === 'constraints'} onRemove={removeConstraint} />
        {isCommitted && (
          <CredentialStatusCard allCredentialTypes={allCredentialTypes} resolvedIds={notes.resolved_credential_ids}
            credentialsCommitted={notes.credentials_committed} isDiscoveringCredentials={isDiscoveringCredentials} />
        )}
      </div>

      {isCommitted && <StartBuildCta canStartBuild={!!canStartBuild} isStarting={isStarting} onStartBuild={onStartBuild} />}
    </aside>
  );
}
