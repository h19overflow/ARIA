import { useState, useCallback, useRef } from 'react'
import { createWorkflow, getJobStatus, submitCredentials } from '@/lib/api'
import type { ARIAState, WorkflowStatus } from '@/types'

interface WorkflowHookState {
  jobId: string | null
  status: WorkflowStatus
  ariaState: ARIAState | null
  error: string | null
  isLoading: boolean
}

interface WorkflowHook extends WorkflowHookState {
  submit: (prompt: string) => Promise<void>
  sendCredentials: (creds: Record<string, string>) => Promise<void>
  reset: () => void
}

const POLL_INTERVAL_MS = 2000
const TERMINAL_STATUSES: WorkflowStatus[] = ['done', 'failed']

const initialState: WorkflowHookState = {
  jobId: null,
  status: 'idle',
  ariaState: null,
  error: null,
  isLoading: false,
}

export function useWorkflow(): WorkflowHook {
  const [state, setState] = useState<WorkflowHookState>(initialState)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const startPolling = useCallback(
    (jobId: string) => {
      stopPolling()
      pollRef.current = setInterval(async () => {
        try {
          const job = await getJobStatus(jobId)
          setState((prev) => ({
            ...prev,
            status: job.status,
            ariaState: job.result ?? prev.ariaState,
            error: job.error ?? null,
            isLoading: !TERMINAL_STATUSES.includes(job.status),
          }))
          if (TERMINAL_STATUSES.includes(job.status)) stopPolling()
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Poll failed'
          setState((prev) => ({ ...prev, error: message, isLoading: false }))
          stopPolling()
        }
      }, POLL_INTERVAL_MS)
    },
    [stopPolling],
  )

  const submit = useCallback(
    async (prompt: string) => {
      setState({ ...initialState, isLoading: true, status: 'planning' })
      try {
        const res = await createWorkflow(prompt)
        setState((prev) => ({ ...prev, jobId: res.job_id }))
        startPolling(res.job_id)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Submission failed'
        setState((prev) => ({ ...prev, error: message, isLoading: false, status: 'failed' }))
      }
    },
    [startPolling],
  )

  const sendCredentials = useCallback(
    async (creds: Record<string, string>) => {
      if (!state.jobId) return
      await submitCredentials(state.jobId, creds)
    },
    [state.jobId],
  )

  const reset = useCallback(() => {
    stopPolling()
    setState(initialState)
  }, [stopPolling])

  return { ...state, submit, sendCredentials, reset }
}
