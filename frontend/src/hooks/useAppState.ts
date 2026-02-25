import { useState, useCallback } from 'react';
import type { ARIAState } from '@/types';

export interface AppStateReturn {
  phase: 0 | 1 | 2;
  conversationId: string | null;
  preflightJobId: string | null;
  buildJobId: string | null;
  preflightAriaState: ARIAState | null;
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
    goToPhase1,
    goToPhase2,
    setBuildJobId,
    reset,
  };
}
