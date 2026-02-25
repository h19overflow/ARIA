import { useConversation } from '@/hooks/useConversation';
import { ChatPanel } from '@/components/conversation/ChatPanel';
import { RequirementsPanel } from '@/components/conversation/RequirementsPanel';

interface ConversationViewProps {
  onStartPreflight: (conversationId: string) => void;
  isStarting?: boolean;
  workflowError?: string | null;
}

export function ConversationView({ onStartPreflight, isStarting, workflowError }: ConversationViewProps) {
  const { conversationId, messages, notes, isStreaming, isCommitted, error, sendMessage, updateNote } =
    useConversation();

  const handleStartPreflight = () => {
    if (!conversationId) return;
    onStartPreflight(conversationId);
  };

  return (
    <div style={{
      display: 'flex',
      height: '100%',
      width: '100%',
      background: 'var(--bg-canvas)',
      color: 'var(--text-primary)',
      overflow: 'hidden',
    }}>
      <RequirementsPanel
        notes={notes}
        isStreaming={isStreaming}
        isCommitted={isCommitted}
        isStarting={isStarting}
        onUpdate={updateNote}
        onStartPreflight={handleStartPreflight}
      />
      <ChatPanel
        messages={messages}
        isStreaming={isStreaming}
        isCommitted={isCommitted}
        error={error}
        workflowError={workflowError}
        isStarting={isStarting}
        onSendMessage={sendMessage}
      />
    </div>
  );
}
