export const PREFLIGHT_NODES = [
  'orchestrator',
  'credential_scanner',
  'credential_guide',
  'credential_saver',
  'handoff',
] as const

export type PreflightNodeName = (typeof PREFLIGHT_NODES)[number]

export type TimelineNodeStatus = 'done' | 'running' | 'pending' | 'error'

export interface TimelineNode {
  name: PreflightNodeName
  status: TimelineNodeStatus
  tools: string[]
  durationMs?: number
  message?: string
}

export const NODE_LABELS: Record<PreflightNodeName, string> = {
  orchestrator: 'Orchestrator',
  credential_scanner: 'Credential Scanner',
  credential_guide: 'Credential Guide',
  credential_saver: 'Credential Saver',
  handoff: 'Handoff',
}

export const NODE_TOOLS: Record<PreflightNodeName, string[]> = {
  orchestrator: ['search_n8n_nodes'],
  credential_scanner: ['list_saved_credentials', 'get_credential_schema', 'check_credentials_resolved'],
  credential_guide: ['search_n8n_nodes', 'get_credential_schema'],
  credential_saver: ['n8n_credential_create'],
  handoff: ['blueprint_builder'],
}
