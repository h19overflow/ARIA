import { useState, useCallback, useRef, useEffect } from 'react';
import { startConversation } from '@/lib/api';
import type { AgentActivity } from '@/types';
import { dispatchConversationEvent } from './dispatchConversationEvent';

export type { AgentActivity } from '@/types';

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

export function applyNoteTaken(prev: ConversationNotes, key: string, value: unknown): ConversationNotes {
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

export function useConversation() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [notes, setNotes] = useState<ConversationNotes>({
    constraints: [], required_integrations: [], raw_notes: {},
  });
  const [activities, setActivities] = useState<AgentActivity[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isCommitted, setIsCommitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const assistantMsgIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    startConversation().then(res => setConversationId(res.conversation_id));
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (!conversationId) return;

    setMessages(prev => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', content, timestamp: new Date() },
    ]);
    setIsStreaming(true);
    setError(null);
    setActivities([]);
    assistantMsgIdRef.current = null;

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

      if (!res.ok || !res.body) throw new Error(`Request failed: ${res.status}`);

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
            dispatchConversationEvent(data, {
              setMessages, setNotes, setActivities, setIsCommitted,
              setIsStreaming, setError, assistantMsgIdRef,
              applyNote: applyNoteTaken,
            });
          } catch {
            // ignore malformed lines
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

  return {
    conversationId, messages, notes, activities,
    isStreaming, isCommitted, error, sendMessage, updateNote,
  };
}
