import type { StateCreator } from 'zustand';
import type { AppStore, PhaseSlice } from './types';

export const createPhaseSlice: StateCreator<AppStore, [], [], PhaseSlice> = (set, get) => ({
  phase: 0,
  preflightJobId: null,
  buildJobId: null,

  goToPhase: (n) => {
    const { conversationId, preflightJobId } = get();
    if (n === 0) { set({ phase: 0 }); return; }
    if (n === 1 && conversationId) { set({ phase: 1 }); return; }
    if (n === 2 && preflightJobId) { set({ phase: 2 }); return; }
  },

  goToPhase1: () => {
    set({ phase: 1 });
  },

  goToPhase2: (preflightId) => {
    set({ preflightJobId: preflightId, phase: 2 });
  },

  setBuildJobId: (id) => set({ buildJobId: id }),

  resetPhase: () => {
    set({
      phase: 0,
      preflightJobId: null,
      buildJobId: null,
      // Also reset conversation state on full reset
      conversationId: null,
      messages: [],
      notes: { constraints: [], required_integrations: [], raw_notes: {} },
      activities: [],
      isStreaming: false,
      isCommitted: false,
      error: null,
      assistantMsgId: null,
    });
  },
});
