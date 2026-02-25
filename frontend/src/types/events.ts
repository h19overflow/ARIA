import type { ARIAState } from './state'

export type EventStage = 'preflight' | 'build' | 'test' | 'fix' | 'system'
export type EventStatus = 'running' | 'success' | 'error' | 'warning'
export type FeedEventType = 'node_start' | 'node_done' | 'interrupt' | 'done' | 'error' | 'info'

export interface FeedEvent {
  id: string
  stage: EventStage
  message: string
  timestamp: Date
  status: EventStatus
  nodeName?: string
  tools?: string[]
  durationMs?: number
  progress?: string
  eventType?: FeedEventType
}

// ─── SSE Envelope ─────────────────────────────────────────────────────────────

export interface SSENodeStartEvent {
  type: 'node_start'
  stage: EventStage
  node_name: string
  message?: string
  status: 'running'
  event_id?: string
  tools?: string[]
  timestamp?: string
  progress?: string
}

export interface SSENodeEvent {
  type: 'node'
  stage: EventStage
  node_name: string
  message?: string
  status: EventStatus
  aria_state?: Record<string, unknown>
  event_id?: string
  tools?: string[]
  duration_ms?: number
  timestamp?: string
  progress?: string
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
  | SSENodeStartEvent
  | SSENodeEvent
  | SSEInterruptEvent
  | SSEDoneEvent
  | SSEErrorEvent
  | SSEPingEvent
