import { useState, useCallback, useRef } from 'react'
import { createWorkflow, submitResume } from '@/lib/api'
import { useEventFeed } from './useEventFeed'
import type { ARIAState, WorkflowStatus, SSEInterruptEvent, FeedEvent } from '@/types'

interface InterruptState {
  kind: 'clarify' | 'credential'
  payload: SSEInterruptEvent['payload']
}

interface WorkflowHookState {
  jobId: string | null
  status: WorkflowStatus
  ariaState: ARIAState | null
  error: string | null
  isLoading: boolean
  interrupt: InterruptState | null
}

export interface WorkflowHook extends WorkflowHookState {
  events: FeedEvent[]
  clearEvents: () => void
  submit: (description: string) => Promise<void>
  resume: (kind: 'clarify' | 'credential', value: string | Record<string, string>) => Promise<void>
  reset: () => void
}

const INITIAL: WorkflowHookState = {
  jobId: null,
  status: 'idle',
  ariaState: null,
  error: null,
  isLoading: false,
  interrupt: null,
}

export function useWorkflow(): WorkflowHook {
  const [state, setState] = useState<WorkflowHookState>(INITIAL)
  const jobIdRef = useRef<string | null>(null)

  const onInterrupt = useCallback(
    (kind: 'clarify' | 'credential', payload: SSEInterruptEvent['payload']) => {
      setState((prev) => ({ ...prev, interrupt: { kind, payload }, isLoading: false }))
    },
    [],
  )

  const onDone = useCallback((ariaState: ARIAState) => {
    setState((prev) => ({
      ...prev,
      ariaState,
      status: 'done',
      isLoading: false,
      interrupt: null,
    }))
  }, [])

  const onError = useCallback((message: string) => {
    setState((prev) => ({ ...prev, error: message, status: 'failed', isLoading: false }))
  }, [])

  const onStateUpdate = useCallback((ariaState: ARIAState) => {
    setState((prev) => ({ ...prev, ariaState, status: (ariaState.status as WorkflowStatus) ?? prev.status }))
  }, [])

  const { events, clearEvents } = useEventFeed(state.jobId, { onInterrupt, onDone, onError, onStateUpdate })

  const submit = useCallback(async (description: string) => {
    setState({ ...INITIAL, isLoading: true, status: 'planning' })
    try {
      const res = await createWorkflow(description)
      jobIdRef.current = res.job_id
      setState((prev) => ({ ...prev, jobId: res.job_id }))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Submission failed'
      setState((prev) => ({ ...prev, error: message, isLoading: false, status: 'failed' }))
    }
  }, [])

  const resume = useCallback(
    async (kind: 'clarify' | 'credential', value: string | Record<string, string>) => {
      const jobId = jobIdRef.current ?? state.jobId
      if (!jobId) return
      setState((prev) => ({ ...prev, interrupt: null, isLoading: true }))
      try {
        await submitResume(jobId, kind, value)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Resume failed'
        setState((prev) => ({ ...prev, error: message, isLoading: false }))
      }
    },
    [state.jobId],
  )

  const reset = useCallback(() => {
    jobIdRef.current = null
    setState(INITIAL)
  }, [])

  return { ...state, events, clearEvents, submit, resume, reset }
}
