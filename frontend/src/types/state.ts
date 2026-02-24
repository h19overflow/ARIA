import type { Topology } from './topology'
import type { ExecutionResult, ClassifiedError } from './execution'
import type { CredentialGuidePayload } from './credentials'
import type { LangChainMessage } from './messages'

export type WorkflowStatus =
  | 'idle'
  | 'planning'
  | 'building'
  | 'testing'
  | 'fixing'
  | 'done'
  | 'failed'
  | 'replanning'

export interface ARIAState {
  status: WorkflowStatus
  intent?: string
  intent_summary?: string
  user_description?: string
  topology?: Topology
  build_phase?: number
  total_phases?: number
  workflow_json?: Record<string, unknown>
  n8n_workflow_id?: string
  webhook_url?: string
  execution_result?: ExecutionResult
  classified_error?: ClassifiedError
  fix_attempts?: number
  pending_credential_types?: string[]
  credential_guide_payload?: CredentialGuidePayload
  messages?: LangChainMessage[]
}

// ─── API contract shapes ──────────────────────────────────────────────────────

export interface CreateWorkflowResponse {
  job_id: string
  status: string
}

export interface JobStatusResponse {
  job_id: string
  status: WorkflowStatus
  result?: ARIAState
  error?: string
}
