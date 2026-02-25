import type { ARIAState, SSEEnvelope, FeedEvent, FeedEventType } from '@/types'

function makeId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

export function makeFeedEvent(
  message: string,
  status: FeedEvent['status'],
  extra?: { nodeName?: string; tools?: string[]; durationMs?: number; progress?: string; eventType?: FeedEventType },
): FeedEvent {
  return { id: makeId(), stage: 'preflight', message, timestamp: new Date(), status, ...extra }
}

export interface EnvelopeResult {
  event: FeedEvent
  ariaState?: ARIAState
  interrupt?: { kind: string; payload: Record<string, unknown> }
  activeNode?: string | null
  status?: 'planning' | 'interrupted' | 'done' | 'failed'
  error?: string
}

export function processEnvelope(envelope: SSEEnvelope): EnvelopeResult | null {
  if (envelope.type === 'node_start') {
    return {
      event: makeFeedEvent(
        envelope.message ?? `${envelope.node_name} starting...`,
        'running',
        { nodeName: envelope.node_name, tools: envelope.tools, progress: envelope.progress, eventType: 'node_start' },
      ),
      activeNode: envelope.node_name,
      status: 'planning',
    }
  }

  if (envelope.type === 'node') {
    return {
      event: makeFeedEvent(
        envelope.message ?? `${envelope.node_name} complete`,
        envelope.status,
        { nodeName: envelope.node_name, tools: envelope.tools, durationMs: envelope.duration_ms, progress: envelope.progress, eventType: 'node_done' },
      ),
      ariaState: envelope.aria_state as ARIAState | undefined,
      activeNode: null,
      status: 'planning',
    }
  }

  if (envelope.type === 'interrupt') {
    return {
      event: makeFeedEvent('Waiting for your input', 'warning', { eventType: 'interrupt' }),
      interrupt: { kind: envelope.kind, payload: envelope.payload as Record<string, unknown> },
      activeNode: null,
      status: 'interrupted',
    }
  }

  if (envelope.type === 'done') {
    return {
      event: makeFeedEvent('Analysis complete', 'success', { eventType: 'done' }),
      ariaState: envelope.aria_state,
      activeNode: null,
      status: 'done',
    }
  }

  if (envelope.type === 'error') {
    return {
      event: makeFeedEvent(envelope.message, 'error', { eventType: 'error' }),
      error: envelope.message,
      activeNode: null,
      status: 'failed',
    }
  }

  return null
}
