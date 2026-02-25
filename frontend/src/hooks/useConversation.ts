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
  // Granular fields from backend
  trigger_type?: string;
  trigger_service?: string;
  trigger_schedule?: string;
  trigger_event?: string;
  transform?: string;
  destination_service?: string;
  destination_action?: string;
  destination_format?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

const GRANULAR_FIELDS = new Set([
  'trigger_type', 'trigger_service', 'trigger_schedule', 'trigger_event',
  'transform', 'destination_service', 'destination_action', 'destination_format',
]);

const KNOWN_FIELDS = new Set([
  'summary', 'trigger', 'destination', 'data_transform', ...GRANULAR_FIELDS,
]);

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
  } else if (KNOWN_FIELDS.has(key)) {
    (next as Record<string, unknown>)[key] = value;
  } else {
    next.raw_notes = { ...(next.raw_notes ?? {}), [key]: String(value) };
  }
  // Synthesize legacy display fields from granular keys
  if (key.startsWith('trigger_')) {
    next.trigger = deriveTrigger(next);
  } else if (key.startsWith('destination_')) {
    next.destination = deriveDestination(next);
  } else if (key === 'transform') {
    next.data_transform = String(value ?? '');
  }
  return next;
}

function deriveTrigger(notes: ConversationNotes): string {
  const parts = [notes.trigger_type, notes.trigger_service, notes.trigger_schedule, notes.trigger_event].filter(Boolean);
  return parts.join(' — ') || notes.trigger || '';
}

function deriveDestination(notes: ConversationNotes): string {
  const parts = [notes.destination_service, notes.destination_action, notes.destination_format].filter(Boolean);
  return parts.join(' — ') || notes.destination || '';
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
