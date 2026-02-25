import { create } from 'zustand';
import type { AppStore } from './types';
import { createPhaseSlice } from './phaseSlice';
import { createConversationSlice } from './conversationSlice';

export const useAppStore = create<AppStore>()((...a) => ({
  ...createPhaseSlice(...a),
  ...createConversationSlice(...a),
}));

export type { Message, ConversationNotes, AppStore } from './types';
