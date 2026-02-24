import type { CreateWorkflowResponse, JobStatusResponse } from '@/types/state'
import { request } from './client'

export function createWorkflow(description?: string, conversationId?: string): Promise<CreateWorkflowResponse> {
  return request<CreateWorkflowResponse>('/workflows', {
    method: 'POST',
    body: JSON.stringify({ description, conversation_id: conversationId }),
  })
}

export function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/jobs/${jobId}`)
}

export function submitResume(
  jobId: string,
  kind: 'clarify' | 'credential',
  value: string | Record<string, string>,
): Promise<void> {
  const body =
    kind === 'clarify'
      ? { action: 'clarify', value }
      : { action: 'provide', credentials: value }
  return request<void>(`/jobs/${jobId}/resume`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
