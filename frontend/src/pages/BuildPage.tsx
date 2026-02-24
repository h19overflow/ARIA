import { PromptInput } from '@/components/build/PromptInput'
import { PipelineStatus } from '@/components/build/PipelineStatus'
import { NodeGraph } from '@/components/build/NodeGraph'
import { EventFeed } from '@/components/build/EventFeed'
import { CredentialDrawer } from '@/components/build/CredentialDrawer'
import type { useWorkflow } from '@/hooks/useWorkflow'
import type { useEventFeed } from '@/hooks/useEventFeed'

type WorkflowState = ReturnType<typeof useWorkflow>
type FeedState = ReturnType<typeof useEventFeed>

interface BuildPageProps {
  workflow: WorkflowState
  feed: FeedState
}

export function BuildPage({ workflow, feed }: BuildPageProps) {
  const { status, ariaState, isLoading, submit, reset, sendCredentials } = workflow
  const { events, clearEvents } = feed

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top section */}
      <div className="flex-none px-4 pt-4 pb-3 space-y-3">
        <PromptInput onSubmit={submit} onReset={reset} isLoading={isLoading} />
        <PipelineStatus
          status={status}
          buildPhase={ariaState?.build_phase}
          totalPhases={ariaState?.total_phases}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-hidden flex gap-3 px-4 pb-3">
        {/* Graph area */}
        <div className="flex-1 glass rounded-xl overflow-hidden relative">
          <div className="absolute inset-0 p-2">
            <NodeGraph topology={ariaState?.topology} status={status} />
          </div>
        </div>

        {/* Event feed sidebar */}
        <div className="w-72 flex-none">
          <EventFeed events={events} onClear={clearEvents} />
        </div>
      </div>

      {/* Credential drawer */}
      <CredentialDrawer
        pendingTypes={ariaState?.pending_credential_types ?? []}
        guide={ariaState?.credential_guide_payload}
        onSubmit={sendCredentials}
      />
    </div>
  )
}
