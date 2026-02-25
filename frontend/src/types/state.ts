export type WorkflowStatus =
  | 'idle'
  | 'planning'
  | 'interrupted'
  | 'building'
  | 'testing'
  | 'fixing'
  | 'done'
  | 'failed'

export type PhaseId = 0 | 1 | 2

export interface ARIAState {
  status?: WorkflowStatus
  intent?: string
  intent_summary?: string
  topology?: import('./topology').Topology
  build_phase?: number
  total_phases?: number
  workflow_json?: Record<string, unknown>
  n8n_workflow_id?: string
  n8n_execution_id?: string
  webhook_url?: string
  execution_result?: import('./execution').ExecutionResult
  classified_error?: import('./execution').ClassifiedError
  fix_attempts?: number
  pending_credential_types?: string[]
  credential_guide_payload?: import('./credentials').CredentialGuidePayload
  messages?: import('./messages').LangChainMessage[]
  build_blueprint?: BuildBlueprint | null
  required_nodes?: string[]
  resolved_credential_ids?: Record<string, string>
  pending_question?: string
  user_description?: string
}

export interface BuildBlueprint {
  intent: string
  required_nodes: string[]
  resolved_credential_ids: Record<string, string>
  topology_hint?: string
}

// API response shapes — aligned with 3-phase API
export interface StartConversationResponse {
  conversation_id: string
}

export interface PreflightResponse {
  preflight_job_id: string
  status: string
}

export interface BuildResponse {
  build_job_id: string
  status: string
}

export interface JobStatusResponse {
  job_id: string
  status: WorkflowStatus
  result?: ARIAState
  error?: string
}

// Global app phase state
export interface PhaseState {
  activePhase: PhaseId
  conversationId: string | null
  preflightJobId: string | null
  buildJobId: string | null
  preflightAriaState: ARIAState | null
  buildAriaState: ARIAState | null
}
