import { useState, useCallback, useRef } from 'react'
import { startPreflight, submitResume } from '@/lib/api'
import { subscribeSSE } from '@/lib/sse'
import type { ARIAState, WorkflowStatus, SSEEnvelope, FeedEvent } from '@/types'
import { processEnvelope, makeFeedEvent } from './preflight-handlers'

export interface PreflightState {
  jobId: string | null
  status: WorkflowStatus
  ariaState: ARIAState | null
  interrupt: { kind: string; payload: Record<string, unknown> } | null
  events: FeedEvent[]
  error: string | null
  activeNode: string | null
}

export interface UsePreflight {
  state: PreflightState
  start: (conversationId: string) => Promise<void>
  resume: (kind: string, value: unknown) => Promise<void>
  patchState: (partial: Partial<ARIAState>) => void
  reset: () => void
}

const INITIAL: PreflightState = {
  jobId: null,
  status: 'idle',
  ariaState: null,
  interrupt: null,
  events: [],
  error: null,
  activeNode: null,
}

export function usePreflight(): UsePreflight {
  const [state, setState] = useState<PreflightState>(INITIAL)
  const jobIdRef = useRef<string | null>(null)
  const unsubRef = useRef<(() => void) | null>(null)

  const appendEvent = useCallback((event: FeedEvent) => {
    setState((prev) => ({ ...prev, events: [event, ...prev.events].slice(0, 100) }))
  }, [])

  const handleEnvelope = useCallback((envelope: SSEEnvelope) => {
    const result = processEnvelope(envelope)
    if (!result) return

    appendEvent(result.event)
    setState((prev) => {
      const next = { ...prev }
      if (result.status) next.status = result.status
      if (result.activeNode !== undefined) next.activeNode = result.activeNode
      if (result.ariaState) next.ariaState = { ...prev.ariaState, ...result.ariaState }
      if (result.interrupt) next.interrupt = result.interrupt
      if (result.error) next.error = result.error
      if (result.status === 'done') next.interrupt = null
      return next
    })
  }, [appendEvent])

  const subscribeToStream = useCallback(
    (jobId: string) => {
      unsubRef.current?.()
      const unsub = subscribeSSE<SSEEnvelope>(`/api/preflight/${jobId}/stream`, {
        onMessage: handleEnvelope,
        onError: () => appendEvent(makeFeedEvent('Stream disconnected', 'warning', { eventType: 'error' })),
      })
      unsubRef.current = unsub
    },
    [handleEnvelope, appendEvent],
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

  const patchState = useCallback((partial: Partial<ARIAState>) => {
    setState((prev) => ({
      ...prev,
      ariaState: prev.ariaState ? { ...prev.ariaState, ...partial } : null,
    }))
  }, [])

  return { state, start, resume, patchState, reset }
}
