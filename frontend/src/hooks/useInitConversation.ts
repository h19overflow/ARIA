import { useEffect } from 'react';
import { useAppStore } from '@/store';
import { startConversation } from '@/lib/api';

export function useInitConversation(): void {
  useEffect(() => {
    const { conversationId, setConversationId } = useAppStore.getState();
    if (conversationId) return;
    startConversation().then((res) => setConversationId(res.conversation_id));
  }, []);
}
