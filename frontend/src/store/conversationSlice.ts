import type { StateCreator } from 'zustand';
import type { AppStore, ConversationSlice } from './types';
import { applyNoteTaken } from './noteUtils';

const INITIAL_NOTES = { constraints: [], required_integrations: [], raw_notes: {} };

export const createConversationSlice: StateCreator<AppStore, [], [], ConversationSlice> = (set, get) => ({
  conversationId: null,
  messages: [],
  notes: { ...INITIAL_NOTES },
  activities: [],
  isStreaming: false,
  isCommitted: false,
  isDiscoveringCredentials: false,
  error: null,
  assistantMsgId: null,

  setConversationId: (id) => set({ conversationId: id }),

  addUserMessage: (content) => {
    set((s) => ({
      messages: [
        ...s.messages,
        { id: crypto.randomUUID(), role: 'user' as const, content, timestamp: new Date() },
      ],
    }));
  },

  appendToken: (chunk) => {
    set((s) => {
      const last = s.messages[s.messages.length - 1];
      if (last?.role === 'assistant' && last.id === s.assistantMsgId) {
        return {
          messages: [
            ...s.messages.slice(0, -1),
            { ...last, content: last.content + chunk },
          ],
        };
      }
      const newId = crypto.randomUUID();
      return {
        assistantMsgId: newId,
        messages: [
          ...s.messages,
          { id: newId, role: 'assistant' as const, content: chunk, timestamp: new Date() },
        ],
      };
    });
  },

  setNotes: (updater) => set((s) => ({ notes: updater(s.notes) })),

  addActivity: (activity) => set((s) => ({ activities: [...s.activities, activity] })),

  clearActivities: () => set({ activities: [] }),

  setIsStreaming: (v) => set({ isStreaming: v }),

  setIsCommitted: (v) => set({ isCommitted: v }),

  setIsDiscoveringCredentials: (v) => set({ isDiscoveringCredentials: v }),

  setError: (err) => set({ error: err }),

  resetAssistantMsgId: () => set({ assistantMsgId: null }),

  updateNote: (key, value) => {
    set((s) => ({ notes: applyNoteTaken(s.notes, key, value) }));
    const { conversationId } = get();
    if (conversationId) {
      fetch(`/api/conversation/${conversationId}/note`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value }),
      }).catch((err) => console.error('Failed to sync note update', err));
    }
  },
});
