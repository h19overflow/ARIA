import { useState, useCallback, useRef } from 'react'
import { startBuild, submitResume } from '@/lib/api'
import { subscribeSSE } from '@/lib/sse'
import type { ARIAState, WorkflowStatus, FeedEvent, SSEEnvelope, SSEInterruptEvent, SSEFixEscalationEvent } from '@/types'

type BuildInterrupt =
  | { kind: 'clarify' | 'credential'; payload: SSEInterruptEvent['payload'] }
  | { kind: 'fix_exhausted'; payload: SSEFixEscalationEvent['payload'] }

export interface BuildState {
  jobId: string | null
  status: WorkflowStatus
  ariaState: ARIAState | null
  interrupt: BuildInterrupt | null
  events: FeedEvent[]
  error: string | null
}

export interface UseBuild {
  state: BuildState
  start: (conversationId: string) => Promise<void>
  resume: (kind: string, value: unknown) => Promise<void>
  reset: () => void
}

const INITIAL: BuildState = {
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

export function useBuild(): UseBuild {
  const [state, setState] = useState<BuildState>(INITIAL)
  const jobIdRef = useRef<string | null>(null)
  const unsubRef = useRef<(() => void) | null>(null)

  const subscribeToJob = useCallback((jobId: string) => {
    unsubRef.current?.()
    unsubRef.current = subscribeSSE<SSEEnvelope>(`/api/build/${jobId}/stream`, {
      onMessage: (envelope) => {
        if (envelope.type === 'node') {
          const event: FeedEvent = {
            id: makeId(),
            stage: envelope.stage,
            message: envelope.message ?? `${envelope.node_name} completed`,
            timestamp: new Date(),
            status: envelope.status,
          }
          setState((prev) => {
            const nextState = envelope.aria_state
              ? { ...prev.ariaState, ...(envelope.aria_state as Partial<ARIAState>) }
              : prev.ariaState
            const nextStatus = (nextState?.status as WorkflowStatus | undefined) ?? prev.status
            return {
              ...prev,
              ariaState: nextState,
              status: nextStatus,
              events: [event, ...prev.events].slice(0, 200),
            }
          })
        } else if (envelope.type === 'interrupt') {
          setState((prev) => ({
            ...prev,
            interrupt: envelope as BuildInterrupt,
          }))
        } else if (envelope.type === 'done') {
          setState((prev) => ({
            ...prev,
            ariaState: envelope.aria_state,
            status: 'done',
            interrupt: null,
          }))
        } else if (envelope.type === 'error') {
          setState((prev) => ({
            ...prev,
            status: 'failed',
            error: envelope.message,
            events: [
              { id: makeId(), stage: 'system', message: envelope.message, timestamp: new Date(), status: 'error' },
              ...prev.events,
            ],
          }))
        }
      },
      onError: () => {
        setState((prev) => ({
          ...prev,
          events: [
            { id: makeId(), stage: 'system', message: 'Stream disconnected', timestamp: new Date(), status: 'warning' },
            ...prev.events,
          ],
        }))
      },
    })
  }, [])

  const start = useCallback(async (conversationId: string) => {
    setState({ ...INITIAL, status: 'building' })
    try {
      const res = await startBuild(conversationId)
      jobIdRef.current = res.build_job_id
      setState((prev) => ({ ...prev, jobId: res.build_job_id }))
      subscribeToJob(res.build_job_id)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start build'
      setState((prev) => ({ ...prev, status: 'failed', error: message }))
    }
  }, [subscribeToJob])

  const resume = useCallback(async (kind: string, value: unknown) => {
    const jobId = jobIdRef.current ?? state.jobId
    if (!jobId) return
    setState((prev) => ({ ...prev, interrupt: null }))
    try {
      await submitResume(
        jobId,
        kind as 'clarify' | 'provide' | 'resume' | 'retry' | 'replan' | 'abort' | 'discuss',
        value as string | Record<string, unknown>,
      )
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Resume failed'
      setState((prev) => ({ ...prev, error: message }))
    }
  }, [state.jobId])

  const reset = useCallback(() => {
    unsubRef.current?.()
    jobIdRef.current = null
    setState(INITIAL)
  }, [])

  return { state, start, resume, reset }
}
