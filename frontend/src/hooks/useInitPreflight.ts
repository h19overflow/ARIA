import { useEffect } from 'react';
import { usePreflightStore } from '@/store/preflightSlice';
import { startPreflightChat } from '@/lib/api';

export function useInitPreflight(conversationId: string | null): void {
  const setPreflightId = usePreflightStore((s) => s.setPreflightId);
  const preflightId = usePreflightStore((s) => s.preflightId);

  useEffect(() => {
    if (!conversationId || preflightId) return;
    startPreflightChat(conversationId)
      .then((res) => setPreflightId(res.preflight_id))
      .catch((err) => console.error('Failed to start preflight:', err));
  }, [conversationId, preflightId, setPreflightId]);
}
