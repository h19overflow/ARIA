import type { AgentActivity, PreflightNotes } from '@/types';

export interface PreflightStoreActions {
  appendToken: (chunk: string) => void;
  setNotes: (updater: (prev: PreflightNotes) => PreflightNotes) => void;
  addActivity: (activity: AgentActivity) => void;
  setIsCommitted: (v: boolean) => void;
  setIsStreaming: (v: boolean) => void;
  setError: (err: string | null) => void;
  resetAssistantMsgId: () => void;
}

export function dispatchPreflightEvent(
  data: Record<string, unknown>,
  actions: PreflightStoreActions,
): void {
  if (data.type === 'token') {
    actions.appendToken(String(data.content ?? ''));
  } else if (data.type === 'tool_event') {
    handleToolEvent(data, actions);
  } else if (data.type === 'tool_start') {
    appendActivity(actions, 'tool_start', data);
  } else if (data.type === 'tool_end') {
    appendActivity(actions, 'tool_end', data);
  } else if (data.type === 'done') {
    actions.setIsStreaming(false);
    actions.resetAssistantMsgId();
  } else if (data.type === 'error') {
    const errPayload = data.error as { message?: string } | undefined;
    actions.setError(errPayload?.message ?? String(data.content ?? 'Unknown error'));
    actions.setIsStreaming(false);
  }
}

function handleToolEvent(
  data: Record<string, unknown>,
  actions: PreflightStoreActions,
): void {
  const tool = data.tool as string | undefined;
  const toolData = data.data as Record<string, unknown> | undefined;

  if (tool === 'save_credential' && toolData) {
    const credType = String(toolData.credential_type ?? '');
    const credId = String(toolData.id ?? '');
    const success = Boolean(toolData.success);
    if (success && credType && credId) {
      actions.setNotes((prev) => ({
        ...prev,
        resolved_credential_ids: { ...prev.resolved_credential_ids, [credType]: credId },
        pending_credential_types: prev.pending_credential_types.filter((t) => t !== credType),
      }));
    }
  } else if (tool === 'commit_preflight' && toolData) {
    actions.setIsCommitted(true);
    if (toolData.summary) {
      actions.setNotes((prev) => ({
        ...prev,
        summary: String(toolData.summary),
        committed: true,
      }));
    }
  }
}

function appendActivity(
  actions: PreflightStoreActions,
  type: 'tool_start' | 'tool_end',
  data: Record<string, unknown>,
): void {
  actions.addActivity({
    id: crypto.randomUUID(),
    type,
    tool: String(data.tool ?? ''),
    args: type === 'tool_start' ? (data.args as Record<string, unknown> | undefined) : undefined,
    result: type === 'tool_end' ? String(data.result ?? '') : undefined,
    timestamp: new Date(),
  });
}
