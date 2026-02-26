import { useState, useEffect, useCallback } from 'react'
import { subscribeSSE } from '@/lib/sse'
import type { FeedEvent, SSEEnvelope, SSEInterruptEvent, SSEFixEscalationEvent, SSEErrorEvent } from '@/types'
import type { ARIAState } from '@/types/state'

interface EventFeedCallbacks {
  onInterrupt: (kind: 'clarify' | 'credential', payload: SSEInterruptEvent['payload']) => void
  onFixExhausted?: (payload: SSEFixEscalationEvent['payload']) => void
  onDone: (ariaState: ARIAState) => void
  onError: (message: string) => void
  onStateUpdate?: (ariaState: ARIAState) => void
}

interface EventFeedHook {
  events: FeedEvent[]
  clearEvents: () => void
}

function makeId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

function nodeEventToFeed(e: Extract<SSEEnvelope, { type: 'node' }>): FeedEvent {
  return {
    id: makeId(),
    stage: e.stage,
    message: e.message ?? `${e.node_name} completed`,
    timestamp: new Date(),
    status: e.status,
  }
}

function makeErrorFeedEvent(message: string): FeedEvent {
  return {
    id: makeId(),
    stage: 'system' as const,
    message,
    timestamp: new Date(),
    status: 'error' as const,
  }
}

function makeDisconnectFeedEvent(): FeedEvent {
  return {
    id: makeId(),
    stage: 'system' as const,
    message: 'Stream disconnected',
    timestamp: new Date(),
    status: 'warning' as const,
  }
}

function handleInterruptEnvelope(
  envelope: SSEInterruptEvent | SSEFixEscalationEvent,
  callbacks: EventFeedCallbacks,
): void {
  if (envelope.kind === 'fix_exhausted') {
    callbacks.onFixExhausted?.(envelope.payload)
  } else {
    callbacks.onInterrupt(envelope.kind, envelope.payload)
  }
}

export function useEventFeed(
  jobId: string | null,
  callbacks: EventFeedCallbacks,
): EventFeedHook {
  const [events, setEvents] = useState<FeedEvent[]>([])
  const clearEvents = useCallback(() => setEvents([]), [])

  useEffect(() => {
    if (!jobId) return

    const unsubscribe = subscribeSSE<SSEEnvelope>(`/api/jobs/${jobId}/stream`, {
      onMessage: (envelope) => {
        if (envelope.type === 'node') {
          setEvents((prev) => [nodeEventToFeed(envelope), ...prev].slice(0, 200))
          if (envelope.aria_state) {
            callbacks.onStateUpdate?.(envelope.aria_state as unknown as ARIAState)
          }
        } else if (envelope.type === 'interrupt') {
          handleInterruptEnvelope(envelope, callbacks)
        } else if (envelope.type === 'done') {
          callbacks.onDone(envelope.aria_state)
        } else if (envelope.type === 'error') {
          setEvents((prev) => [makeErrorFeedEvent((envelope as SSEErrorEvent).message), ...prev])
          callbacks.onError((envelope as SSEErrorEvent).message)
        }
        // ping → ignore
      },
      onError: () => {
        setEvents((prev) => [makeDisconnectFeedEvent(), ...prev])
      },
    })

    return unsubscribe
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId])

  return { events, clearEvents }
}
