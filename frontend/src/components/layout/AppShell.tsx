import { lazy, Suspense } from 'react';
import { useAppStore } from '@/store';
import PhaseHeader from './PhaseHeader';

const ConversationView = lazy(() =>
  import('@/views/ConversationView').then((m) => ({ default: m.ConversationView }))
);
const PreflightPage = lazy(() =>
  import('@/pages/PreflightPage').then((m) => ({ default: m.PreflightPage }))
);
const BuildPage = lazy(() =>
  import('@/pages/BuildPage').then((m) => ({ default: m.BuildPage }))
);

function PhaseFallback() {
  return (
    <div style={{
      flex: 1,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-canvas)',
    }}>
      <div style={{
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: 'var(--text-muted)',
      }} />
    </div>
  );
}

function BuildPhaseWrapper({ preflightId }: { preflightId: string }) {
  return <BuildPage preflightId={preflightId} />;
}

export function AppShell() {
  const phase = useAppStore((s) => s.phase);
  const conversationId = useAppStore((s) => s.conversationId);
  const preflightId = useAppStore((s) => s.preflightId);
  const goToPhase = useAppStore((s) => s.goToPhase);
  const goToPhase1 = useAppStore((s) => s.goToPhase1);
  const goToPhase2 = useAppStore((s) => s.goToPhase2);
  const resetPhase = useAppStore((s) => s.resetPhase);

  const completedPhases = new Set<number>([
    ...(phase > 0 ? [0] : []),
    ...(phase > 1 ? [1] : []),
  ]);

  const handleStartBuild = (preflightId: string) => {
    goToPhase2(preflightId);
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      background: 'var(--bg-canvas)',
      overflow: 'hidden',
    }}>
      <PhaseHeader
        activePhase={phase}
        completedPhases={completedPhases}
        onPhaseClick={goToPhase}
        onReset={resetPhase}
      />

      <main style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <Suspense fallback={<PhaseFallback />}>
          {phase === 0 && (
            <ConversationView
              onStartPreflight={goToPhase1}
            />
          )}
          {phase === 1 && conversationId && (
            <PreflightPage
              conversationId={conversationId}
              onStartBuild={handleStartBuild}
            />
          )}
          {phase === 2 && preflightId && (
            <BuildPhaseWrapper preflightId={preflightId} />
          )}
        </Suspense>
      </main>
    </div>
  );
}
