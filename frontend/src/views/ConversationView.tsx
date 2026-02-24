import { useState, useEffect } from 'react';
import { useConversation } from '../hooks/useConversation';
import { ChatPanel } from '../components/conversation/ChatPanel';
import { ScratchpadPanel } from '../components/conversation/ScratchpadPanel';

interface ConversationViewProps {
  onStartBuilding: (conversationId: string) => Promise<void>;
  isStarting?: boolean;
  workflowError?: string | null;
}

async function startConversation(): Promise<string> {
  try {
    const res = await fetch('/api/conversation/start', { method: 'POST' });
    if (res.ok) {
      const data = (await res.json()) as { conversation_id?: string; id?: string };
      return data.conversation_id ?? data.id ?? crypto.randomUUID();
    }
  } catch {
    // fall through to fallback
  }
  return crypto.randomUUID();
}

export function ConversationView({ onStartBuilding, isStarting, workflowError }: ConversationViewProps) {
  const [conversationId, setConversationId] = useState<string | null>(null);

  useEffect(() => {
    startConversation().then(setConversationId);
  }, []);

  const { messages, notes, isStreaming, isCommitted, error, sendMessage, updateNote } =
    useConversation(conversationId);

  const handleStartBuilding = async () => {
    if (!conversationId) return;
    await onStartBuilding(conversationId);
  };

  return (
    <div
      style={{
        display: 'flex',
        height: '100%',
        width: '100%',
        background: 'var(--bg-base)',
        color: 'var(--text-primary)',
        overflow: 'hidden',
      }}
    >
      <ScratchpadPanel notes={notes} onUpdate={updateNote} />
      <ChatPanel
        messages={messages}
        isStreaming={isStreaming}
        isCommitted={isCommitted}
        error={error}
        workflowError={workflowError}
        isStarting={isStarting}
        onSendMessage={sendMessage}
        onStartBuilding={handleStartBuilding}
      />
    </div>
  );
}
