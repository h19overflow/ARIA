import { lazy, Suspense } from 'react';
import { useAppStore } from '@/store';
import PhaseHeader from './PhaseHeader';

const ConversationView = lazy(() =>
  import('@/views/ConversationView').then((m) => ({ default: m.ConversationView }))
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

function BuildPhaseWrapper({ conversationId }: { conversationId: string }) {
  return <BuildPage conversationId={conversationId} />;
}

export function AppShell() {
  const phase = useAppStore((s) => s.phase);
  const conversationId = useAppStore((s) => s.conversationId);
  const goToPhase = useAppStore((s) => s.goToPhase);
  const goToBuild = useAppStore((s) => s.goToBuild);
  const resetPhase = useAppStore((s) => s.resetPhase);

  const completedPhases = new Set<number>([
    ...(phase > 0 ? [0] : []),
  ]);

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
              onStartBuild={goToBuild}
            />
          )}
          {phase === 1 && conversationId && (
            <BuildPhaseWrapper conversationId={conversationId} />
          )}
        </Suspense>
      </main>
    </div>
  );
}
