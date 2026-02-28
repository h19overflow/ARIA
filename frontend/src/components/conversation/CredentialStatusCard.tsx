import { CheckCircle2, Clock, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
import type { ConversationNotes } from '@/store';
import { formatCredentialDisplayName } from '@/lib/credentials';

interface CredentialStatusCardProps {
  allCredentialTypes: string[];
  resolvedIds?: Record<string, string>;
  credentialsCommitted?: boolean;
  isDiscoveringCredentials?: boolean;
}

export function getAllCredentialTypes(notes: ConversationNotes): string[] {
  return [
    ...new Set([
      ...Object.keys(notes.resolved_credential_ids ?? {}),
      ...(notes.pending_credential_types ?? []),
    ]),
  ];
}

export function CredentialStatusCard({
  allCredentialTypes,
  resolvedIds,
  credentialsCommitted,
  isDiscoveringCredentials,
}: CredentialStatusCardProps) {
  return (
    <div className={clsx('req-field-card')}
      style={{ borderRadius: '8px', padding: '10px 12px', border: '1px solid var(--border-subtle)', background: 'transparent' }}>
      <span style={{ display: 'block', fontSize: '0.6rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '7px' }}>
        Connections
      </span>
      {isDiscoveringCredentials && allCredentialTypes.length === 0 ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          <Loader2 size={12} className="animate-spin" />
          <span>Discovering required credentials...</span>
        </div>
      ) : allCredentialTypes.length === 0 ? (
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
          {credentialsCommitted ? 'No credentials needed' : 'Scanning...'}
        </span>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {allCredentialTypes.map((type) => {
            const isResolved = type in (resolvedIds ?? {});
            return (
              <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
                {isResolved
                  ? <CheckCircle2 size={12} style={{ color: 'var(--color-success)' }} />
                  : <Clock size={12} style={{ color: 'var(--text-muted)' }} />}
                <span style={{ color: isResolved ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                  {formatCredentialDisplayName(type)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
