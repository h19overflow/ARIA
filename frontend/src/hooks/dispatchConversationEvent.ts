import type { Dispatch, SetStateAction, MutableRefObject } from 'react';
import type { AgentActivity } from '@/types';
import type { Message, ConversationNotes } from './useConversation';

interface EventSetters {
  setMessages: Dispatch<SetStateAction<Message[]>>;
  setNotes: Dispatch<SetStateAction<ConversationNotes>>;
  setActivities: Dispatch<SetStateAction<AgentActivity[]>>;
  setIsCommitted: Dispatch<SetStateAction<boolean>>;
  setIsStreaming: Dispatch<SetStateAction<boolean>>;
  setError: Dispatch<SetStateAction<string | null>>;
  assistantMsgIdRef: MutableRefObject<string | null>;
  applyNote: (prev: ConversationNotes, key: string, value: unknown) => ConversationNotes;
}

export function dispatchConversationEvent(
  data: Record<string, unknown>,
  setters: EventSetters,
): void {
  const {
    setMessages, setNotes, setActivities, setIsCommitted,
    setIsStreaming, setError, assistantMsgIdRef, applyNote,
  } = setters;

  if (data.type === 'token') {
    handleToken(data, setMessages, assistantMsgIdRef);
  } else if (data.type === 'tool_event') {
    handleToolEvent(data, setNotes, setIsCommitted, applyNote);
  } else if (data.type === 'tool_start') {
    appendActivity(setActivities, 'tool_start', data);
  } else if (data.type === 'tool_end') {
    appendActivity(setActivities, 'tool_end', data);
  } else if (data.type === 'note_taken') {
    handleNoteTaken(data, setNotes, applyNote);
  } else if (data.type === 'committed') {
    handleCommitted(data, setNotes, setIsCommitted);
  } else if (data.type === 'done') {
    setIsStreaming(false);
    assistantMsgIdRef.current = null;
  } else if (data.type === 'error') {
    const errPayload = data.error as { message?: string } | undefined;
    setError(errPayload?.message ?? 'Unknown error');
    setIsStreaming(false);
  }
}

function handleToken(
  data: Record<string, unknown>,
  setMessages: Dispatch<SetStateAction<Message[]>>,
  assistantMsgIdRef: MutableRefObject<string | null>,
): void {
  const chunk = String(data.content ?? '');
  setMessages(prev => {
    const last = prev[prev.length - 1];
    if (last?.role === 'assistant' && last.id === assistantMsgIdRef.current) {
      return [...prev.slice(0, -1), { ...last, content: last.content + chunk }];
    }
    const newId = crypto.randomUUID();
    assistantMsgIdRef.current = newId;
    return [...prev, { id: newId, role: 'assistant', content: chunk, timestamp: new Date() }];
  });
}

function handleToolEvent(
  data: Record<string, unknown>,
  setNotes: Dispatch<SetStateAction<ConversationNotes>>,
  setIsCommitted: Dispatch<SetStateAction<boolean>>,
  applyNote: (prev: ConversationNotes, key: string, value: unknown) => ConversationNotes,
): void {
  const tool = data.tool as string | undefined;
  const toolData = data.data as Record<string, unknown> | undefined;
  if (tool === 'take_note' && toolData) {
    setNotes(prev => applyNote(prev, String(toolData.key ?? ''), toolData.value));
  } else if (tool === 'batch_notes' && toolData) {
    const notes = toolData.notes as { key: string; value: unknown }[] | undefined;
    if (notes) {
      setNotes(prev => notes.reduce((acc, n) => applyNote(acc, n.key, n.value), prev));
    }
  } else if (tool === 'commit_notes' && toolData) {
    setIsCommitted(true);
    if (toolData.summary) setNotes(prev => ({ ...prev, summary: String(toolData.summary) }));
  }
}

function appendActivity(
  setActivities: Dispatch<SetStateAction<AgentActivity[]>>,
  type: 'tool_start' | 'tool_end',
  data: Record<string, unknown>,
): void {
  setActivities(prev => [...prev, {
    id: crypto.randomUUID(),
    type,
    tool: String(data.tool ?? ''),
    args: type === 'tool_start' ? data.args as Record<string, unknown> | undefined : undefined,
    result: type === 'tool_end' ? String(data.result ?? '') : undefined,
    timestamp: new Date(),
  }]);
}

function handleNoteTaken(
  data: Record<string, unknown>,
  setNotes: Dispatch<SetStateAction<ConversationNotes>>,
  applyNote: (prev: ConversationNotes, key: string, value: unknown) => ConversationNotes,
): void {
  const payload = data.payload as { key: string; value: unknown } | undefined;
  if (payload) setNotes(prev => applyNote(prev, payload.key, payload.value));
}

function handleCommitted(
  data: Record<string, unknown>,
  setNotes: Dispatch<SetStateAction<ConversationNotes>>,
  setIsCommitted: Dispatch<SetStateAction<boolean>>,
): void {
  setIsCommitted(true);
  const payload = data.payload as { summary?: string } | undefined;
  if (payload?.summary) setNotes(prev => ({ ...prev, summary: payload.summary }));
}
