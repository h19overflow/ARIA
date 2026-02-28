import { X } from 'lucide-react';
import { clsx } from 'clsx';

interface ConstraintsListProps {
  constraints: string[];
  isHighlighted: boolean;
  onRemove: (idx: number) => void;
}

export function ConstraintsList({ constraints, isHighlighted, onRemove }: ConstraintsListProps) {
  return (
    <div className={clsx('req-field-card', isHighlighted && 'req-field-just-updated')}
      style={{ borderRadius: '8px', padding: '10px 12px', border: '1px solid var(--border-subtle)', background: 'transparent' }}>
      <span style={{ display: 'block', fontSize: '0.6rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '7px' }}>
        Constraints
      </span>
      {constraints.length === 0 ? (
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>Not yet captured...</span>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {constraints.map((c, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', fontSize: '0.75rem', color: 'var(--text-primary)' }}>
              <span style={{ flex: 1, lineHeight: 1.5 }}>{c}</span>
              <button onClick={() => onRemove(i)} style={{ color: 'var(--text-muted)', lineHeight: 0, flexShrink: 0, transition: 'color 150ms ease' }}
                onMouseEnter={e => (e.currentTarget.style.color = 'var(--color-error)')}
                onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>
                <X size={11} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
