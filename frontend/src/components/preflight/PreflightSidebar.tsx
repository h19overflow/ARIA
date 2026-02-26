import { CheckCircle, Clock } from 'lucide-react';
import type { PreflightNotes } from '@/types';

interface PreflightSidebarProps {
  notes: PreflightNotes;
  intentSummary?: string;
  isCommitted: boolean;
  isStreaming: boolean;
  onContinueToBuild: () => void;
}

export function PreflightSidebar({
  notes,
  intentSummary,
  isCommitted,
  isStreaming,
  onContinueToBuild,
}: PreflightSidebarProps) {
  const allTypes = getAllCredentialTypes(notes);

  return (
    <aside style={{
      width: 280,
      minWidth: 280,
      borderRight: '1px solid var(--border-subtle)',
      background: 'var(--bg-surface)',
      display: 'flex',
      flexDirection: 'column',
      padding: '16px',
      gap: '16px',
      overflowY: 'auto',
    }}>
      <SidebarSection label="Workflow">
        {intentSummary
          ? <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{intentSummary}</p>
          : <p style={{ fontSize: 13, color: 'var(--text-muted)', fontStyle: 'italic' }}>Loading intent...</p>}
      </SidebarSection>

      <SidebarSection label="Connections">
        {allTypes.length === 0
          ? <p style={{ fontSize: 13, color: 'var(--text-muted)', fontStyle: 'italic' }}>Scanning...</p>
          : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {allTypes.map((type) => (
                <CredentialRow key={type} type={type} notes={notes} />
              ))}
            </div>
          )}
      </SidebarSection>

      <div style={{ marginTop: 'auto' }}>
        <button
          onClick={onContinueToBuild}
          disabled={!isCommitted || isStreaming}
          style={{
            width: '100%',
            padding: '10px 16px',
            borderRadius: 8,
            border: 'none',
            background: isCommitted ? 'var(--accent-primary)' : 'var(--bg-hover)',
            color: isCommitted ? 'white' : 'var(--text-muted)',
            fontSize: 13,
            fontWeight: 600,
            cursor: isCommitted ? 'pointer' : 'not-allowed',
            transition: 'all 0.15s',
          }}
        >
          {isCommitted ? 'Continue to Build \u2192' : 'Waiting for credentials...'}
        </button>
      </div>
    </aside>
  );
}

function SidebarSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{
        fontSize: 11,
        fontWeight: 600,
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        marginBottom: 8,
      }}>
        {label}
      </div>
      {children}
    </div>
  );
}

interface CredentialRowProps {
  type: string;
  notes: PreflightNotes;
}

function CredentialRow({ type, notes }: CredentialRowProps) {
  const isResolved = type in notes.resolved_credential_ids;
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      padding: '6px 10px',
      borderRadius: 6,
      background: isResolved
        ? 'var(--success-subtle, rgba(34,197,94,0.08))'
        : 'var(--bg-hover)',
    }}>
      {isResolved
        ? <CheckCircle size={14} color="var(--success, #22c55e)" />
        : <Clock size={14} color="var(--text-muted)" />}
      <span style={{ fontSize: 13, color: isResolved ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
        {type}
      </span>
      {isResolved && (
        <span style={{ fontSize: 11, color: 'var(--success, #22c55e)', marginLeft: 'auto' }}>
          Connected
        </span>
      )}
    </div>
  );
}

function getAllCredentialTypes(notes: PreflightNotes): string[] {
  const resolved = Object.keys(notes.resolved_credential_ids);
  const pending = notes.pending_credential_types;
  return [...new Set([...resolved, ...pending])];
}
