export type WorkflowStatus =
  | 'idle'
  | 'planning'
  | 'interrupted'
  | 'building'
  | 'testing'
  | 'fixing'
  | 'replanning'
  | 'done'
  | 'failed'

export type PhaseId = 0 | 1

export interface ARIAState {
  status?: WorkflowStatus
  intent?: string
  intent_summary?: string
  topology?: import('./topology').Topology
  nodes_to_build?: Array<{ node_name: string; node_type: string; role: string; credential_type?: string | null; connected_to: string[] }>
  planned_edges?: unknown[]
  node_build_results?: Array<{ node_name: string; node_json: unknown; credentials_used: unknown; validation_passed: boolean; validation_errors: string[] }>
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
  hitl_explanation?: string | null

}

export interface BuildBlueprint {
  intent: string
  required_nodes: string[]
  credential_ids: Record<string, string>
  topology?: import('./topology').Topology
  user_description?: string
}

// API response shapes — aligned with 3-phase API
export interface StartConversationResponse {
  conversation_id: string
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
  buildJobId: string | null
}
