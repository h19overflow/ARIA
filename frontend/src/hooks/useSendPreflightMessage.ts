import { useCallback, useRef } from 'react';
import { usePreflightStore } from '@/store/preflightSlice';
import { dispatchPreflightEvent } from '@/store/dispatchPreflightEvent';

export function useSendPreflightMessage(): (content: string) => Promise<void> {
  const abortRef = useRef<AbortController | null>(null);

  return useCallback(async (content: string) => {
    const state = usePreflightStore.getState();
    if (!state.preflightId) return;

    state.addUserMessage(content);
    state.setIsStreaming(true);
    state.setError(null);
    state.clearActivities();
    state.resetAssistantMsgId();

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(`/api/preflight/${state.preflightId}/message`, {
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
            const actions = usePreflightStore.getState();
            dispatchPreflightEvent(data, actions);
          } catch {
            // ignore malformed lines
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      usePreflightStore
        .getState()
        .setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      usePreflightStore.getState().setIsStreaming(false);
    }
  }, []);
}
