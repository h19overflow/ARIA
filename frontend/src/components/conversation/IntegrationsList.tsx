import { X } from 'lucide-react';
import { clsx } from 'clsx';

interface IntegrationsListProps {
  integrations: string[];
  isHighlighted: boolean;
  onRemove: (idx: number) => void;
}

export function IntegrationsList({ integrations, isHighlighted, onRemove }: IntegrationsListProps) {
  return (
    <div className={clsx('req-field-card', isHighlighted && 'req-field-just-updated')}
      style={{ borderRadius: '8px', padding: '10px 12px', border: '1px solid var(--border-subtle)', background: 'transparent' }}>
      <span style={{ display: 'block', fontSize: '0.6rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '7px' }}>
        Integrations
      </span>
      {integrations.length === 0 ? (
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>Not yet captured...</span>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
          {integrations.map((integ, i) => (
            <span key={i} className="integration-chip">
              {integ}
              <button onClick={() => onRemove(i)} style={{ lineHeight: 0, color: 'var(--text-muted)', opacity: 0.6 }}><X size={10} /></button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
