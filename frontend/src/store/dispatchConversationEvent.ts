import type { ConversationNotes } from './types';
import type { AgentActivity } from '@/types';
import { applyNoteTaken } from './noteUtils';

export interface StoreActions {
  appendToken: (chunk: string) => void;
  setNotes: (updater: (prev: ConversationNotes) => ConversationNotes) => void;
  addActivity: (activity: AgentActivity) => void;
  setIsCommitted: (v: boolean) => void;
  setIsStreaming: (v: boolean) => void;
  setError: (err: string | null) => void;
  resetAssistantMsgId: () => void;
}

export function dispatchConversationEvent(
  data: Record<string, unknown>,
  actions: StoreActions,
): void {
  if (data.type === 'token') {
    actions.appendToken(String(data.content ?? ''));
  } else if (data.type === 'tool_event') {
    handleToolEvent(data, actions);
  } else if (data.type === 'tool_start') {
    appendActivity(actions, 'tool_start', data);
  } else if (data.type === 'tool_end') {
    appendActivity(actions, 'tool_end', data);
  } else if (data.type === 'note_taken') {
    handleNoteTaken(data, actions);
  } else if (data.type === 'committed') {
    handleCommitted(data, actions);
  } else if (data.type === 'done') {
    actions.setIsStreaming(false);
    actions.resetAssistantMsgId();
  } else if (data.type === 'error') {
    const errPayload = data.error as { message?: string } | undefined;
    actions.setError(errPayload?.message ?? 'Unknown error');
    actions.setIsStreaming(false);
  }
}

function handleToolEvent(data: Record<string, unknown>, actions: StoreActions): void {
  const tool = data.tool as string | undefined;
  const toolData = data.data as Record<string, unknown> | undefined;
  if (tool === 'take_note' && toolData) {
    actions.setNotes((prev) => applyNoteTaken(prev, String(toolData.key ?? ''), toolData.value));
  } else if (tool === 'batch_notes' && toolData) {
    const notes = toolData.notes as { key: string; value: unknown }[] | undefined;
    if (notes) {
      actions.setNotes((prev) => notes.reduce((acc, n) => applyNoteTaken(acc, n.key, n.value), prev));
    }
  } else if (tool === 'commit_notes' && toolData) {
    actions.setIsCommitted(true);
    if (toolData.summary) {
      actions.setNotes((prev) => ({ ...prev, summary: String(toolData.summary) }));
    }
  }
}

function appendActivity(actions: StoreActions, type: 'tool_start' | 'tool_end', data: Record<string, unknown>): void {
  actions.addActivity({
    id: crypto.randomUUID(),
    type,
    tool: String(data.tool ?? ''),
    args: type === 'tool_start' ? data.args as Record<string, unknown> | undefined : undefined,
    result: type === 'tool_end' ? String(data.result ?? '') : undefined,
    timestamp: new Date(),
  });
}

function handleNoteTaken(data: Record<string, unknown>, actions: StoreActions): void {
  const payload = data.payload as { key: string; value: unknown } | undefined;
  if (payload) {
    actions.setNotes((prev) => applyNoteTaken(prev, payload.key, payload.value));
  }
}

function handleCommitted(data: Record<string, unknown>, actions: StoreActions): void {
  actions.setIsCommitted(true);
  const payload = data.payload as { summary?: string } | undefined;
  if (payload?.summary) {
    actions.setNotes((prev) => ({ ...prev, summary: payload.summary }));
  }
}
