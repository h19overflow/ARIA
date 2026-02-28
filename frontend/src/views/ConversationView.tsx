import { useAppStore } from '@/store';
import { useSendMessage } from '@/hooks/useSendMessage';
import { useInitConversation } from '@/hooks/useInitConversation';
import { ChatPanel } from '@/components/conversation/ChatPanel';
import { RequirementsPanel } from '@/components/conversation/RequirementsPanel';
import { PageGuide } from '@/components/shared/PageGuide';
import { CONVERSATION_GUIDE } from '@/components/shared/guide-content';

interface ConversationViewProps {
  onStartBuild: () => void;
  isStarting?: boolean;
  workflowError?: string | null;
}

export function ConversationView({ onStartBuild, isStarting, workflowError }: ConversationViewProps) {
  useInitConversation();
  const sendMessage = useSendMessage();

  const messages = useAppStore((s) => s.messages);
  const notes = useAppStore((s) => s.notes);
  const activities = useAppStore((s) => s.activities);
  const isStreaming = useAppStore((s) => s.isStreaming);
  const isCommitted = useAppStore((s) => s.isCommitted);
  const isDiscoveringCredentials = useAppStore((s) => s.isDiscoveringCredentials);
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
        isDiscoveringCredentials={isDiscoveringCredentials}
        onUpdate={updateNote}
        onStartBuild={onStartBuild}
      />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '12px 16px 0' }}>
          <PageGuide title="How to describe your workflow" steps={CONVERSATION_GUIDE} storageKey="guide-phase0" />
        </div>
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
    </div>
  );
}
