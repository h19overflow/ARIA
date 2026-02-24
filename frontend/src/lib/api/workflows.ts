import type { CreateWorkflowResponse, JobStatusResponse } from '@/types/state'
import { request } from './client'

export function createWorkflow(prompt: string): Promise<CreateWorkflowResponse> {
  return request<CreateWorkflowResponse>('/workflows', {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  })
}

export function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/jobs/${jobId}`)
}

export function submitCredentials(
  jobId: string,
  credentials: Record<string, string>,
): Promise<void> {
  return request<void>(`/jobs/${jobId}/credentials`, {
    method: 'POST',
    body: JSON.stringify({ credentials }),
  })
}
