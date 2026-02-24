import { PromptInput } from '@/components/build/PromptInput'
import { NodeGraph } from '@/components/build/NodeGraph'
import { EventFeed } from '@/components/build/EventFeed'
import { CredentialDrawer } from '@/components/build/CredentialDrawer'
import { ClarifyDrawer } from '@/components/build/ClarifyDrawer'
import { GraphEmptyState } from '@/components/build/GraphEmptyState'
import type { WorkflowHook } from '@/hooks/useWorkflow'

interface BuildPageProps {
  workflow: WorkflowHook
}

export function BuildPage({ workflow }: BuildPageProps) {
  const {
    status, ariaState, isLoading, interrupt,
    events, clearEvents,
    submit, resume, reset,
  } = workflow

  const hasTopology = Boolean(ariaState?.topology?.nodes?.length)

  return (
    <div className="flex h-full overflow-hidden">
      {/* Graph canvas */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-hidden relative graph-canvas">
          {hasTopology
            ? <NodeGraph topology={ariaState!.topology!} status={status} />
            : <GraphEmptyState status={status} />
          }

          {/* Clarify drawer — absolute over the graph */}
          {interrupt?.kind === 'clarify' && (
            <ClarifyDrawer
              question={interrupt.payload.question ?? ''}
              onSubmit={(answer) => resume('clarify', answer)}
              isLoading={isLoading}
            />
          )}
        </div>

        <div className="flex-none p-4 border-t border-[var(--border-subtle)]">
          <PromptInput onSubmit={submit} onReset={reset} isLoading={isLoading} />
        </div>
      </div>

      {/* Event feed */}
      <div className="w-72 flex-none border-l border-[var(--border-subtle)]">
        <EventFeed events={events} onClear={clearEvents} />
      </div>

      {/* Credential drawer */}
      {interrupt?.kind === 'credential' && (
        <CredentialDrawer
          pendingTypes={interrupt.payload.pending_types ?? []}
          guide={ariaState?.credential_guide_payload}
          onSubmit={(creds) => resume('credential', creds)}
        />
      )}
    </div>
  )
}
