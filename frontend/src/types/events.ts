import type { ARIAState } from './state'

export type EventStage = 'preflight' | 'build' | 'test' | 'fix' | 'system'
export type EventStatus = 'running' | 'success' | 'error' | 'warning'

export interface FeedEvent {
  id: string
  stage: EventStage
  message: string
  timestamp: Date
  status: EventStatus
}

// ─── SSE Envelope ─────────────────────────────────────────────────────────────

export interface SSENodeEvent {
  type: 'node'
  stage: EventStage
  node_name: string
  message?: string
  status: EventStatus
  aria_state?: Record<string, unknown>
}

export interface SSEInterruptEvent {
  type: 'interrupt'
  kind: 'clarify' | 'credential'
  payload: {
    question?: string
    pending_types?: string[]
    guide?: Record<string, unknown>
  }
}

export interface SSEDoneEvent {
  type: 'done'
  aria_state: ARIAState
}

export interface SSEErrorEvent {
  type: 'error'
  message: string
}

export interface SSEPingEvent {
  type: 'ping'
}

export type SSEEnvelope =
  | SSENodeEvent
  | SSEInterruptEvent
  | SSEDoneEvent
  | SSEErrorEvent
  | SSEPingEvent
