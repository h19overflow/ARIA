import { create } from 'zustand';
import type { AgentActivity, PreflightNotes } from '@/types';
import type { Message } from './types';

interface PreflightStore {
  preflightId: string | null;
  messages: Message[];
  notes: PreflightNotes;
  activities: AgentActivity[];
  isStreaming: boolean;
  isCommitted: boolean;
  error: string | null;
  assistantMsgId: string | null;

  setPreflightId: (id: string) => void;
  addUserMessage: (content: string) => void;
  appendToken: (chunk: string) => void;
  addActivity: (activity: AgentActivity) => void;
  clearActivities: () => void;
  setIsStreaming: (v: boolean) => void;
  setIsCommitted: (v: boolean) => void;
  setError: (err: string | null) => void;
  resetAssistantMsgId: () => void;
  setNotes: (updater: (prev: PreflightNotes) => PreflightNotes) => void;
  resetPreflight: () => void;
}

const INITIAL_NOTES: PreflightNotes = {
  required_nodes: [],
  resolved_credential_ids: {},
  pending_credential_types: [],
  summary: '',
  committed: false,
};

export const usePreflightStore = create<PreflightStore>((set) => ({
  preflightId: null,
  messages: [],
  notes: { ...INITIAL_NOTES },
  activities: [],
  isStreaming: false,
  isCommitted: false,
  error: null,
  assistantMsgId: null,

  setPreflightId: (id) => set({ preflightId: id }),

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

  addActivity: (activity) => set((s) => ({ activities: [...s.activities, activity] })),
  clearActivities: () => set({ activities: [] }),
  setIsStreaming: (v) => set({ isStreaming: v }),
  setIsCommitted: (v) => set({ isCommitted: v }),
  setError: (err) => set({ error: err }),
  resetAssistantMsgId: () => set({ assistantMsgId: null }),
  setNotes: (updater) => set((s) => ({ notes: updater(s.notes) })),

  resetPreflight: () =>
    set({
      preflightId: null,
      messages: [],
      notes: { ...INITIAL_NOTES },
      activities: [],
      isStreaming: false,
      isCommitted: false,
      error: null,
      assistantMsgId: null,
    }),
}));

