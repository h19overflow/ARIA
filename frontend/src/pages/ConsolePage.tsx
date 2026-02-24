import { MetricsBar } from '@/components/console/MetricsBar'
import { StateViewer } from '@/components/console/StateViewer'
import { MessageThread } from '@/components/console/MessageThread'
import type { ARIAState } from '@/types'

interface ConsolePageProps {
  ariaState: ARIAState | null
}

export function ConsolePage({ ariaState }: ConsolePageProps) {
  return (
    <div className="h-full overflow-y-auto px-4 py-4 space-y-4">
      <MetricsBar ariaState={ariaState} />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <StateViewer ariaState={ariaState} />
        <MessageThread messages={ariaState?.messages} />
      </div>
    </div>
  )
}
