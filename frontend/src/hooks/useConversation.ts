import { useState, useCallback, useRef } from 'react';

export interface ConversationNotes {
  summary?: string;
  trigger?: string;
  destination?: string;
  data_transform?: string | null;
  constraints?: string[];
  required_integrations?: string[];
  raw_notes?: Record<string, string>;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

function applyNoteTaken(prev: ConversationNotes, key: string, value: unknown): ConversationNotes {
  const next = { ...prev };
  if (value === null) {
    if (key in next) {
      delete (next as Record<string, unknown>)[key];
    } else if (next.raw_notes && key in next.raw_notes) {
      next.raw_notes = { ...next.raw_notes };
      delete next.raw_notes[key];
    }
  } else if (key === 'constraints' || key === 'required_integrations') {
    const current = (next as Record<string, unknown>)[key];
    const arr = Array.isArray(current) ? current : [];
    if (Array.isArray(value)) {
      (next as Record<string, unknown>)[key] = value;
    } else if (typeof value === 'string' && !arr.includes(value)) {
      (next as Record<string, unknown>)[key] = [...arr, value];
    }
  } else if (['summary', 'trigger', 'destination', 'data_transform'].includes(key)) {
    (next as Record<string, unknown>)[key] = value;
  } else {
    next.raw_notes = { ...(next.raw_notes ?? {}), [key]: String(value) };
  }
  return next;
}

export function useConversation(conversationId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [notes, setNotes] = useState<ConversationNotes>({
    constraints: [],
    required_integrations: [],
    raw_notes: {},
  });
  const [isStreaming, setIsStreaming] = useState(false);
  const [isCommitted, setIsCommitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const assistantMsgIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    if (!conversationId) return;

    // Optimistic user message
    setMessages(prev => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', content, timestamp: new Date() },
    ]);
    setIsStreaming(true);
    setError(null);
    assistantMsgIdRef.current = null;

    // Cancel any in-flight stream
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(`/api/conversation/${conversationId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error(`Request failed: ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (!raw || raw === '[DONE]') continue;

          try {
            const data = JSON.parse(raw) as Record<string, unknown>;

            if (data.type === 'token') {
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
            } else if (data.type === 'note_taken' || data.type === 'tool_event') {
              // note_taken: { payload: {key, value} }
              // tool_event from take_note: { tool: "take_note", data: {key, value} }
              // tool_event from commit_notes: { tool: "commit_notes", data: {summary} }
              if (data.type === 'tool_event') {
                const tool = data.tool as string | undefined;
                const toolData = data.data as Record<string, unknown> | undefined;
                if (tool === 'take_note' && toolData) {
                  setNotes(prev => applyNoteTaken(prev, String(toolData.key ?? ''), toolData.value));
                } else if (tool === 'commit_notes' && toolData) {
                  setIsCommitted(true);
                  if (toolData.summary) setNotes(prev => ({ ...prev, summary: String(toolData.summary) }));
                }
              } else {
                const payload = data.payload as { key: string; value: unknown } | undefined;
                if (payload) setNotes(prev => applyNoteTaken(prev, payload.key, payload.value));
              }
            } else if (data.type === 'committed') {
              setIsCommitted(true);
              const payload = data.payload as { summary?: string } | undefined;
              if (payload?.summary) {
                setNotes(prev => ({ ...prev, summary: payload.summary }));
              }
            } else if (data.type === 'done') {
              setIsStreaming(false);
              assistantMsgIdRef.current = null;
            } else if (data.type === 'error') {
              const errPayload = data.error as { message?: string } | undefined;
              setError(errPayload?.message ?? 'Unknown error');
              setIsStreaming(false);
            }
          } catch {
            // ignore malformed line
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setIsStreaming(false);
    }
  }, [conversationId]);

  const updateNote = useCallback((key: string, value: string | null) => {
    setNotes(prev => applyNoteTaken(prev, key, value));

    if (conversationId) {
      fetch(`/api/conversation/${conversationId}/note`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value }),
      }).catch(err => console.error('Failed to sync note update', err));
    }
  }, [conversationId]);

  return { messages, notes, isStreaming, isCommitted, error, sendMessage, updateNote };
}
