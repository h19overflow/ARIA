import { ArrowRight, Loader2, CheckCircle2 } from 'lucide-react';

interface StartBuildCtaProps {
  canStartBuild: boolean;
  isStarting?: boolean;
  onStartBuild: () => void;
}

export function StartBuildCta({ canStartBuild, isStarting, onStartBuild }: StartBuildCtaProps) {
  return (
    <div style={{ padding: '12px 14px 16px', borderTop: '1px solid var(--border-subtle)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
        <CheckCircle2 size={13} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
        <span style={{ fontSize: '0.72rem', color: 'var(--color-success)', fontWeight: 500 }}>Requirements captured</span>
      </div>
      <button
        className="btn-run-preflight"
        onClick={onStartBuild}
        disabled={!canStartBuild || isStarting}
      >
        {isStarting
          ? <><Loader2 size={15} className="animate-spin" /> Starting build...</>
          : canStartBuild
            ? <>Start Build <ArrowRight size={15} /></>
            : <>Waiting for credentials...</>
        }
      </button>
    </div>
  );
}
