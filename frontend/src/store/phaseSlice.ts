import type { StateCreator } from 'zustand';
import type { AppStore, PhaseSlice } from './types';

export const createPhaseSlice: StateCreator<AppStore, [], [], PhaseSlice> = (set, get) => ({
  phase: 0,
  buildJobId: null,

  goToPhase: (n) => {
    const { conversationId } = get();
    if (n === 0) { set({ phase: 0 }); return; }
    if (n === 1 && conversationId) { set({ phase: 1 }); return; }
  },

  goToBuild: () => {
    const { conversationId, isCommitted, notes } = get();
    if (conversationId && isCommitted && notes.credentials_committed) {
      set({ phase: 1 });
    }
  },

  setBuildJobId: (id) => set({ buildJobId: id }),

  resetPhase: () => {
    set({
      phase: 0,
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
