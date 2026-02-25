import { useState, useCallback, useRef } from 'react'
import { startPreflight, submitResume } from '@/lib/api'
import { subscribeSSE } from '@/lib/sse'
import type { ARIAState, WorkflowStatus, SSEEnvelope, FeedEvent } from '@/types'

export interface PreflightState {
  jobId: string | null
  status: WorkflowStatus
  ariaState: ARIAState | null
  interrupt: { kind: string; payload: Record<string, unknown> } | null
  events: FeedEvent[]
  error: string | null
}

export interface UsePreflight {
  state: PreflightState
  start: (conversationId: string) => Promise<void>
  resume: (kind: string, value: unknown) => Promise<void>
  reset: () => void
}

const INITIAL: PreflightState = {
  jobId: null,
  status: 'idle',
  ariaState: null,
  interrupt: null,
  events: [],
  error: null,
}

function makeId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

function makeFeedEvent(message: string, status: FeedEvent['status']): FeedEvent {
  return { id: makeId(), stage: 'preflight', message, timestamp: new Date(), status }
}

export function usePreflight(): UsePreflight {
  const [state, setState] = useState<PreflightState>(INITIAL)
  const jobIdRef = useRef<string | null>(null)
  const unsubRef = useRef<(() => void) | null>(null)

  const appendEvent = useCallback((event: FeedEvent) => {
    setState((prev) => ({ ...prev, events: [event, ...prev.events].slice(0, 100) }))
  }, [])

  const subscribeToStream = useCallback(
    (jobId: string) => {
      unsubRef.current?.()
      const unsub = subscribeSSE<SSEEnvelope>(`/api/preflight/${jobId}/stream`, {
        onMessage: (envelope) => {
          if (envelope.type === 'node') {
            appendEvent(makeFeedEvent(envelope.message ?? `${envelope.node_name} complete`, envelope.status))
            if (envelope.aria_state) {
              setState((prev) => ({
                ...prev,
                ariaState: { ...prev.ariaState, ...(envelope.aria_state as ARIAState) },
                status: 'planning',
              }))
            }
          } else if (envelope.type === 'interrupt') {
            appendEvent(makeFeedEvent('Waiting for your input', 'warning'))
            setState((prev) => ({
              ...prev,
              interrupt: { kind: envelope.kind, payload: envelope.payload as Record<string, unknown> },
              status: 'interrupted',
            }))
          } else if (envelope.type === 'done') {
            appendEvent(makeFeedEvent('Analysis complete', 'success'))
            setState((prev) => ({ ...prev, ariaState: envelope.aria_state, status: 'done', interrupt: null }))
          } else if (envelope.type === 'error') {
            appendEvent(makeFeedEvent(envelope.message, 'error'))
            setState((prev) => ({ ...prev, error: envelope.message, status: 'failed' }))
          }
        },
        onError: () => {
          appendEvent(makeFeedEvent('Stream disconnected', 'warning'))
        },
      })
      unsubRef.current = unsub
    },
    [appendEvent],
  )

  const start = useCallback(
    async (conversationId: string) => {
      setState({ ...INITIAL, status: 'planning' })
      try {
        const res = await startPreflight({ conversation_id: conversationId })
        jobIdRef.current = res.preflight_job_id
        setState((prev) => ({ ...prev, jobId: res.preflight_job_id }))
        subscribeToStream(res.preflight_job_id)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to start analysis'
        setState((prev) => ({ ...prev, error: message, status: 'failed' }))
      }
    },
    [subscribeToStream],
  )

  const resume = useCallback(async (kind: string, value: unknown) => {
    const jobId = jobIdRef.current ?? state.jobId
    if (!jobId) return
    setState((prev) => ({ ...prev, interrupt: null, status: 'planning' }))
    try {
      const resumeKind = kind === 'credential' ? 'provide' : 'clarify'
      await submitResume(jobId, resumeKind as Parameters<typeof submitResume>[1], value as string)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Resume failed'
      setState((prev) => ({ ...prev, error: message }))
    }
  }, [state.jobId])

  const reset = useCallback(() => {
    unsubRef.current?.()
    unsubRef.current = null
    jobIdRef.current = null
    setState(INITIAL)
  }, [])

  return { state, start, resume, reset }
}
