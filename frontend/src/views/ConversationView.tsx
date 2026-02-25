import { useAppStore } from '@/store';
import { useSendMessage } from '@/hooks/useSendMessage';
import { useInitConversation } from '@/hooks/useInitConversation';
import { ChatPanel } from '@/components/conversation/ChatPanel';
import { RequirementsPanel } from '@/components/conversation/RequirementsPanel';

interface ConversationViewProps {
  onStartPreflight: () => void;
  isStarting?: boolean;
  workflowError?: string | null;
}

export function ConversationView({ onStartPreflight, isStarting, workflowError }: ConversationViewProps) {
  useInitConversation();
  const sendMessage = useSendMessage();

  const messages = useAppStore((s) => s.messages);
  const notes = useAppStore((s) => s.notes);
  const activities = useAppStore((s) => s.activities);
  const isStreaming = useAppStore((s) => s.isStreaming);
  const isCommitted = useAppStore((s) => s.isCommitted);
  const error = useAppStore((s) => s.error);
  const updateNote = useAppStore((s) => s.updateNote);

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
        onStartPreflight={onStartPreflight}
      />
      <ChatPanel
        messages={messages}
        activities={activities}
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
