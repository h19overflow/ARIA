import { useEffect } from 'react'
import type { ARIAState } from '@/types'
import { usePreflight } from '@/hooks/usePreflight'
import { PreflightHeader } from '@/components/preflight/PreflightHeader'
import { StepsPanel } from '@/components/preflight/StepsPanel'
import { BlueprintPanel } from '@/components/preflight/BlueprintPanel'
import { CredentialModal } from '@/components/preflight/CredentialModal'

interface PreflightPageProps {
  conversationId: string
  onStartBuild: (preflightJobId: string, ariaState: ARIAState) => void
}

export function PreflightPage({ conversationId, onStartBuild }: PreflightPageProps) {
  const { state, start, resume, reset } = usePreflight()

  useEffect(() => {
    start(conversationId)
    return () => reset()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId])

  function handleStartBuild() {
    if (state.jobId && state.ariaState) {
      onStartBuild(state.jobId, state.ariaState)
    }
  }

  function handleCredentialSubmit(credentials: Record<string, unknown>) {
    resume('credential', credentials)
  }

  function handleCredentialDismiss() {
    resume('credential', {})
  }

  function handleConnectMissing() {
    // Surfacing the existing credential interrupt modal
    // The interrupt will be set by the SSE stream when credentials are needed
  }

  return (
    <div className="flex flex-col h-full bg-canvas animate-fade-in">
      <PreflightHeader status={state.status} ariaState={state.ariaState} />

      <div className="flex flex-1 overflow-hidden">
        <StepsPanel
          ariaState={state.ariaState}
          status={state.status}
          events={state.events}
        />
        <BlueprintPanel
          ariaState={state.ariaState}
          status={state.status}
          onStartBuild={handleStartBuild}
          onConnectMissing={handleConnectMissing}
        />
      </div>

      {state.error && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-40 animate-slide-up">
          <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-error/15 border border-error/30 text-sm text-error/90">
            {state.error}
          </div>
        </div>
      )}

      <CredentialModal
        interrupt={state.interrupt}
        onSubmit={handleCredentialSubmit}
        onDismiss={handleCredentialDismiss}
      />
    </div>
  )
}
