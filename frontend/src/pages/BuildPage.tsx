import { useEffect } from 'react'
import { NodeGraph } from '@/components/build/NodeGraph'
import { BuildEmptyState } from '@/components/build/BuildEmptyState'
import { BuildHeader } from '@/components/build/BuildHeader'
import { BuildSidebar } from '@/components/build/BuildSidebar'
import { SuccessBanner } from '@/components/build/SuccessBanner'
import { ClarifyDrawer } from '@/components/build/ClarifyDrawer'
import { FixEscalationPanel } from '@/components/build/FixEscalationPanel'
import { CredentialDrawer } from '@/components/build/CredentialDrawer'
import { useBuild } from '@/hooks/useBuild'
import { PageGuide } from '@/components/shared/PageGuide'
import { BUILD_GUIDE } from '@/components/shared/guide-content'
interface BuildPageProps {
  preflightId: string
}

export function BuildPage({ preflightId }: BuildPageProps) {
  const { state, start, resume, reset } = useBuild()
  const { status, ariaState, interrupt, events, error } = state

  useEffect(() => {
    start(preflightId)
    return () => reset()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preflightId])

  const hasTopology = Boolean(
    ariaState?.workflow_json ||
    ariaState?.phase_node_map?.length ||
    ariaState?.topology?.nodes?.length
  )
  const isDone = status === 'done'

  function handleClarifySubmit(answer: string) {
    resume('clarify', answer)
  }

  function handleCredentialSubmit(creds: Record<string, string>) {
    return resume('provide', creds)
  }

  function handleFixEscalationAction(action: 'retry' | 'replan' | 'abort') {
    resume(action, action)
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <BuildHeader status={status} ariaState={ariaState} />

      <div className="flex flex-1 overflow-hidden">
        {/* Main canvas */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          <div className="absolute top-3 left-3 right-3 z-10">
            <PageGuide title="How the build works" steps={BUILD_GUIDE} storageKey="guide-phase2" />
          </div>
          <div className="flex-1 overflow-hidden graph-canvas relative">
            {hasTopology ? (
              <NodeGraph
                topology={ariaState?.topology ?? null}
                ariaState={ariaState}
                status={status}
                events={events}
              />
            ) : (
              <BuildEmptyState
                status={status}
                error={error}
                onRetry={() => start(preflightId)}
              />
            )}

            {/* HITL: fix escalation panel — shown when fix budget exhausted */}
            {interrupt?.kind === 'fix_exhausted' && (
              <FixEscalationPanel
                explanation={interrupt.payload.explanation ?? ''}
                error={interrupt.payload.error ?? {}}
                fixAttempts={interrupt.payload.fix_attempts ?? 0}
                n8nUrl={interrupt.payload.n8n_url ?? ''}
                onAction={handleFixEscalationAction}
              />
            )}

            {/* HITL: clarify drawer — shown for mid-build clarification questions */}
            {interrupt?.kind === 'clarify' && (
              <ClarifyDrawer
                question={interrupt.payload.question ?? ''}
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
