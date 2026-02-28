import type { ConversationNotes } from './types';
import type { AgentActivity } from '@/types';
import { applyNoteTaken } from './noteUtils';

export interface StoreActions {
  appendToken: (chunk: string) => void;
  setNotes: (updater: (prev: ConversationNotes) => ConversationNotes) => void;
  addActivity: (activity: AgentActivity) => void;
  setIsCommitted: (v: boolean) => void;
  setIsDiscoveringCredentials: (v: boolean) => void;
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
    const tool = data.tool as string | undefined;
    const toolData = data.data as Record<string, unknown> | undefined;
    if (tool && toolData) TOOL_HANDLERS[tool]?.(toolData, actions);
  } else if (data.type === 'tool_start') {
    appendActivity(actions, 'tool_start', data);
  } else if (data.type === 'tool_end') {
    appendActivity(actions, 'tool_end', data);
  } else if (data.type === 'error') {
    const errPayload = data.error as { message?: string } | undefined;
    actions.setError(errPayload?.message ?? String(data.content ?? 'Unknown error'));
    actions.setIsStreaming(false);
  }
}

type ToolHandler = (toolData: Record<string, unknown>, actions: StoreActions) => void;

function handleTakeNote(toolData: Record<string, unknown>, actions: StoreActions): void {
  actions.setNotes((prev) => applyNoteTaken(prev, String(toolData.key ?? ''), toolData.value));
}

function handleBatchNotes(toolData: Record<string, unknown>, actions: StoreActions): void {
  const notes = toolData.notes as { key: string; value: unknown }[] | undefined;
  if (notes) {
    actions.setNotes((prev) => notes.reduce((acc, n) => applyNoteTaken(acc, n.key, n.value), prev));
  }
}

function handleCommitNotes(toolData: Record<string, unknown>, actions: StoreActions): void {
  actions.setIsCommitted(true);
  actions.setIsDiscoveringCredentials(true);
  if (toolData.summary) {
    actions.setNotes((prev) => ({ ...prev, summary: String(toolData.summary) }));
  }
}

function handleScanCredentials(toolData: Record<string, unknown>, actions: StoreActions): void {
  actions.setIsDiscoveringCredentials(false);
  const resolved = toolData.resolved as Array<{ type: string; id: string }> | undefined;
  const pending = toolData.pending as string[] | undefined;
  const requiredNodes = toolData.required_nodes as string[] | undefined;
  actions.setNotes((prev) => ({
    ...prev,
    resolved_credential_ids: {
      ...prev.resolved_credential_ids,
      ...(resolved ? Object.fromEntries(resolved.map((r) => [r.type, r.id])) : {}),
    },
    pending_credential_types: pending ?? prev.pending_credential_types ?? [],
    required_nodes: requiredNodes ?? prev.required_nodes ?? [],
  }));
}

function handleSaveCredential(toolData: Record<string, unknown>, actions: StoreActions): void {
  const credType = String(toolData.credential_type ?? '');
  const credId = String(toolData.id ?? '');
  if (Boolean(toolData.success) && credType && credId) {
    actions.setNotes((prev) => ({
      ...prev,
      resolved_credential_ids: { ...(prev.resolved_credential_ids ?? {}), [credType]: credId },
      pending_credential_types: (prev.pending_credential_types ?? []).filter((t) => t !== credType),
    }));
  }
}

function handleCommitPreflight(_toolData: Record<string, unknown>, actions: StoreActions): void {
  actions.setNotes((prev) => ({ ...prev, credentials_committed: true }));
}

const TOOL_HANDLERS: Record<string, ToolHandler> = {
  take_note: handleTakeNote,
  batch_notes: handleBatchNotes,
  commit_notes: handleCommitNotes,
  scan_credentials: handleScanCredentials,
  save_credential: handleSaveCredential,
  commit_preflight: handleCommitPreflight,
};

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
