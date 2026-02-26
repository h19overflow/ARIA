import { usePreflightStore } from '@/store/preflightSlice';
import { PreflightView } from '@/views/PreflightView';

interface PreflightPageProps {
  conversationId: string;
  onStartBuild: (preflightId: string) => void;
}

export function PreflightPage({ conversationId: _conversationId, onStartBuild }: PreflightPageProps) {
  const preflightId = usePreflightStore((s) => s.preflightId);

  function handleContinueToBuild() {
    if (preflightId) {
      onStartBuild(preflightId);
    }
  }

  return (
    <div className="flex flex-col h-full bg-canvas animate-fade-in">
      <PreflightView onContinueToBuild={handleContinueToBuild} />
    </div>
  );
}
