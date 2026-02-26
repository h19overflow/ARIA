import type { AgentActivity } from '@/types';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface ConversationNotes {
  summary?: string;
  trigger?: string;
  destination?: string;
  data_transform?: string | null;
  constraints?: string[];
  required_integrations?: string[];
  raw_notes?: Record<string, string>;
  trigger_type?: string;
  trigger_service?: string;
  trigger_schedule?: string;
  trigger_event?: string;
  transform?: string;
  destination_service?: string;
  destination_action?: string;
  destination_format?: string;
  required_nodes?: string[];
  resolved_credential_ids?: Record<string, string>;
  pending_credential_types?: string[];
  credentials_committed?: boolean;
}

export interface PhaseSlice {
  phase: 0 | 1;
  buildJobId: string | null;
  goToPhase: (n: 0 | 1) => void;
  goToBuild: () => void;
  setBuildJobId: (id: string) => void;
  resetPhase: () => void;
}

export interface ConversationSlice {
  conversationId: string | null;
  messages: Message[];
  notes: ConversationNotes;
  activities: AgentActivity[];
  isStreaming: boolean;
  isCommitted: boolean;
  error: string | null;
  assistantMsgId: string | null;
  setConversationId: (id: string) => void;
  addUserMessage: (content: string) => void;
  appendToken: (chunk: string) => void;
  setNotes: (updater: (prev: ConversationNotes) => ConversationNotes) => void;
  addActivity: (activity: AgentActivity) => void;
  clearActivities: () => void;
  setIsStreaming: (v: boolean) => void;
  setIsCommitted: (v: boolean) => void;
  setError: (err: string | null) => void;
  resetAssistantMsgId: () => void;
  updateNote: (key: string, value: string | null) => void;
}

export type AppStore = PhaseSlice & ConversationSlice;
