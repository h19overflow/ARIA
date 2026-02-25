import { useEffect } from 'react'
import { NodeGraph } from '@/components/build/NodeGraph'
import { BuildEmptyState } from '@/components/build/BuildEmptyState'
import { BuildHeader } from '@/components/build/BuildHeader'
import { BuildSidebar } from '@/components/build/BuildSidebar'
import { SuccessBanner } from '@/components/build/SuccessBanner'
import { ClarifyDrawer } from '@/components/build/ClarifyDrawer'
import { CredentialDrawer } from '@/components/build/CredentialDrawer'
import { useBuild } from '@/hooks/useBuild'
import type { ARIAState } from '@/types'

interface BuildPageProps {
  preflightJobId: string
  preflightAriaState: ARIAState | null
}

export function BuildPage({ preflightJobId, preflightAriaState: _ }: BuildPageProps) {
  const { state, start, resume, reset } = useBuild()
  const { status, ariaState, interrupt, events, error } = state

  useEffect(() => {
    start(preflightJobId)
    return () => reset()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preflightJobId])

  const topology = ariaState?.topology
  const hasTopology = Boolean(topology?.nodes?.length)
  const isDone = status === 'done'

  function handleClarifySubmit(answer: string) {
    resume('clarify', answer)
  }

  function handleCredentialSubmit(creds: Record<string, string>) {
    return resume('provide', creds)
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <BuildHeader status={status} ariaState={ariaState} />

      <div className="flex flex-1 overflow-hidden">
        {/* Main canvas */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          <div className="flex-1 overflow-hidden graph-canvas relative">
            {hasTopology ? (
              <NodeGraph
                topology={topology!}
                status={status}
                events={events}
              />
            ) : (
              <BuildEmptyState
                status={status}
                error={error}
                onRetry={() => start(preflightJobId)}
              />
            )}

            {/* HITL: clarify drawer overlaid on canvas */}
            {interrupt?.kind === 'clarify' && (
              <ClarifyDrawer
                question={(interrupt.payload.question as string) ?? ''}
                onSubmit={handleClarifySubmit}
                isLoading={false}
              />
            )}

            {/* Success banner overlaid at bottom of canvas */}
            {isDone && (
              <SuccessBanner
                webhookUrl={ariaState?.webhook_url}
                n8nWorkflowId={ariaState?.n8n_workflow_id}
                fixAttempts={ariaState?.fix_attempts ?? 0}
              />
            )}
          </div>

          {/* HITL: credential drawer below canvas */}
          {interrupt?.kind === 'credential' && (
            <CredentialDrawer
              pendingTypes={(interrupt.payload.pending_types as string[]) ?? []}
              guide={ariaState?.credential_guide_payload}
              onSubmit={handleCredentialSubmit as (creds: Record<string, string>) => Promise<void>}
            />
          )}
        </div>

        <BuildSidebar ariaState={ariaState} status={status} events={events} />
      </div>
    </div>
  )
}
