import { lazy, Suspense } from 'react';
import { useAppState } from '@/hooks/useAppState';
import PhaseHeader from './PhaseHeader';
import type { ARIAState } from '@/types';

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

function BuildPhaseWrapper({ preflightJobId, preflightAriaState }: { preflightJobId: string; preflightAriaState: ARIAState | null }) {
  return <BuildPage preflightJobId={preflightJobId} preflightAriaState={preflightAriaState} />;
}

export function AppShell() {
  const app = useAppState();

  const completedPhases = new Set<number>([
    ...(app.phase > 0 ? [0] : []),
    ...(app.phase > 1 ? [1] : []),
  ]);

  const handleStartBuild = (pJobId: string, pState: ARIAState) => {
    app.goToPhase2(pJobId, pState);
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
        activePhase={app.phase}
        completedPhases={completedPhases}
        onReset={app.reset}
      />

      <main style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <Suspense fallback={<PhaseFallback />}>
          {app.phase === 0 && (
            <ConversationView
              onStartPreflight={app.goToPhase1}
            />
          )}
          {app.phase === 1 && app.conversationId && (
            <PreflightPage
              conversationId={app.conversationId}
              onStartBuild={handleStartBuild}
            />
          )}
          {app.phase === 2 && app.preflightJobId && (
            <BuildPhaseWrapper
              preflightJobId={app.preflightJobId}
              preflightAriaState={app.preflightAriaState}
            />
          )}
        </Suspense>
      </main>
    </div>
  );
}
