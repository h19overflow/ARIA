import { request } from './client'
import type {
  StartConversationResponse,
  BuildResponse,
  JobStatusResponse,
} from '@/types'

// Phase 0 — Conversation
export const startConversation = (): Promise<StartConversationResponse> =>
  request('/conversation/start', { method: 'POST' })

// Phase 1 — Build
export const startBuild = (conversationId: string): Promise<BuildResponse> =>
  request('/build', { method: 'POST', body: JSON.stringify({ conversation_id: conversationId }) })

// Jobs (all types)
export const getJobStatus = (jobId: string): Promise<JobStatusResponse> =>
  request(`/jobs/${jobId}`)

// HITL resume
export const submitResume = (
  jobId: string,
  kind: 'clarify' | 'provide' | 'resume' | 'retry' | 'replan' | 'abort' | 'discuss',
  value?: string | Record<string, unknown>
): Promise<void> => {
  let body: Record<string, unknown>
  if (kind === 'clarify') {
    body = { action: 'clarify', value }
  } else if (kind === 'provide') {
    body = { action: 'provide', credentials: value }
  } else if (kind === 'discuss') {
    body = { action: 'discuss', message: value }
  } else {
    body = { action: kind }
  }
  return request(`/jobs/${jobId}/resume`, { method: 'POST', body: JSON.stringify(body) })
}

// Direct credential saving (bypasses LangGraph interrupt)
export const saveCredential = (
  credentialType: string,
  name: string,
  data: Record<string, string>
): Promise<{ credential_id: string; credential_type: string; name: string }> =>
  request('/credentials', {
    method: 'POST',
    body: JSON.stringify({ credential_type: credentialType, name, data })
  })
