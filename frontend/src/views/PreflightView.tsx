import { useAppStore } from '@/store';
import { usePreflightStore } from '@/store/preflightSlice';
import { useInitPreflight } from '@/hooks/useInitPreflight';
import { useSendPreflightMessage } from '@/hooks/useSendPreflightMessage';
import { ChatPanel } from '@/components/conversation/ChatPanel';
import { PreflightSidebar } from '@/components/preflight/PreflightSidebar';

interface PreflightViewProps {
  onContinueToBuild: () => void;
}

export function PreflightView({ onContinueToBuild }: PreflightViewProps) {
  const conversationId = useAppStore((s) => s.conversationId);
  useInitPreflight(conversationId);
  const sendMessage = useSendPreflightMessage();

  const messages = usePreflightStore((s) => s.messages);
  const notes = usePreflightStore((s) => s.notes);
  const activities = usePreflightStore((s) => s.activities);
  const isStreaming = usePreflightStore((s) => s.isStreaming);
  const isCommitted = usePreflightStore((s) => s.isCommitted);
  const error = usePreflightStore((s) => s.error);
  const conversationNotes = useAppStore((s) => s.notes);

  return (
    <div style={{
      display: 'flex',
      height: '100%',
      width: '100%',
      background: 'var(--bg-canvas)',
      color: 'var(--text-primary)',
      overflow: 'hidden',
    }}>
      <PreflightSidebar
        notes={notes}
        intentSummary={conversationNotes.summary}
        isCommitted={isCommitted}
        isStreaming={isStreaming}
        onContinueToBuild={onContinueToBuild}
      />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <ChatPanel
          messages={messages}
          activities={activities}
          isStreaming={isStreaming}
          isCommitted={isCommitted}
          error={error}
          onSendMessage={sendMessage}
        />
      </div>
    </div>
  );
}
