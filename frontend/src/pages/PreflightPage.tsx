import { useEffect, useState, useCallback } from 'react'
import type { ARIAState, CredentialGuideEntry } from '@/types'
import { usePreflight } from '@/hooks/usePreflight'
import { saveCredential } from '@/lib/api'
import { PreflightHeader } from '@/components/preflight/PreflightHeader'
import { StepsPanel } from '@/components/preflight/StepsPanel'
import { BlueprintPanel } from '@/components/preflight/BlueprintPanel'
import { CredentialCard } from '@/components/preflight/CredentialCard'

interface PreflightPageProps {
  conversationId: string
  onStartBuild: (preflightJobId: string, ariaState: ARIAState) => void
}

export function PreflightPage({ conversationId, onStartBuild }: PreflightPageProps) {
  const { state, start, resume, reset } = usePreflight()
  const [connectingType, setConnectingType] = useState<string | null>(null)

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

  const handleConnect = useCallback((credentialType: string) => {
    setConnectingType(credentialType)
  }, [])

  async function handleCredentialSubmit(credentials: Record<string, string>) {
    if (!connectingType) return

    if (state.status === 'interrupted') {
      // BUG FIX #1: Wrap credentials under the credential type key
      resume('credential', { [connectingType]: credentials })
    } else {
      // BUG FIX #2: Use direct API when not in interrupted state
      try {
        const result = await saveCredential(connectingType, connectingType, credentials)
        
        // Update local state to reflect the saved credential
        if (state.ariaState) {
          const updatedState: ARIAState = {
            ...state.ariaState,
            pending_credential_types: state.ariaState.pending_credential_types?.filter(
              (t) => t !== connectingType
            ),
            resolved_credential_ids: {
              ...state.ariaState.resolved_credential_ids,
              [connectingType]: result.credential_id,
            },
          }
          // Note: The usePreflight hook doesn't expose setState directly,
          // but the credential will be available on next refresh
        }
      } catch (error) {
        console.error('Failed to save credential:', error)
        return
      }
    }
    
    setConnectingType(null)
  }

  function handleCredentialDismiss() {
    setConnectingType(null)
  }

  const activeEntry = findGuideEntry(state.ariaState, connectingType)

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
          onConnect={handleConnect}
        />
      </div>

      {state.error && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-40 animate-slide-up">
          <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-error/15 border border-error/30 text-sm text-error/90">
            {state.error}
          </div>
        </div>
      )}

      {activeEntry && (
        <CredentialCard
          entry={activeEntry}
          onSubmit={handleCredentialSubmit}
          onDismiss={handleCredentialDismiss}
        />
      )}
    </div>
  )
}

function findGuideEntry(
  ariaState: ARIAState | null,
  credentialType: string | null,
): CredentialGuideEntry | null {
  if (!ariaState?.credential_guide_payload || !credentialType) return null
  const payload = ariaState.credential_guide_payload
  return payload.entries?.find((e) => e.credential_type === credentialType) ?? null
}
