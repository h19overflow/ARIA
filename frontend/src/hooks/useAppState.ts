import { useState, useCallback } from 'react';
import type { ARIAState } from '@/types';

export interface AppStateReturn {
  phase: 0 | 1 | 2;
  conversationId: string | null;
  preflightJobId: string | null;
  buildJobId: string | null;
  preflightAriaState: ARIAState | null;
  goToPhase: (n: 0 | 1 | 2) => void;
  goToPhase1: (convId: string) => void;
  goToPhase2: (pJobId: string, pState: ARIAState) => void;
  setBuildJobId: (id: string) => void;
  reset: () => void;
}

export function useAppState(): AppStateReturn {
  const [phase, setPhase] = useState<0 | 1 | 2>(0);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [preflightJobId, setPreflightJobId] = useState<string | null>(null);
  const [buildJobId, setBuildJobId] = useState<string | null>(null);
  const [preflightAriaState, setPreflightAriaState] = useState<ARIAState | null>(null);

  const goToPhase = useCallback((n: 0 | 1 | 2) => {
    // Only allow navigating to phases that have the required data
    if (n === 0) { setPhase(0); return; }
    if (n === 1 && conversationId) { setPhase(1); return; }
    if (n === 2 && preflightJobId) { setPhase(2); return; }
  }, [conversationId, preflightJobId]);

  const goToPhase1 = useCallback((convId: string) => {
    setConversationId(convId);
    setPhase(1);
  }, []);

  const goToPhase2 = useCallback((pJobId: string, pState: ARIAState) => {
    setPreflightJobId(pJobId);
    setPreflightAriaState(pState);
    setPhase(2);
  }, []);

  const reset = useCallback(() => {
    setPhase(0);
    setConversationId(null);
    setPreflightJobId(null);
    setBuildJobId(null);
    setPreflightAriaState(null);
  }, []);

  return {
    phase,
    conversationId,
    preflightJobId,
    buildJobId,
    preflightAriaState,
    goToPhase,
    goToPhase1,
    goToPhase2,
    setBuildJobId,
    reset,
  };
}
