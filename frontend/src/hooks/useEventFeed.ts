import { useState, useEffect, useCallback } from 'react'
import { subscribeSSE } from '@/lib/sse'
import type { FeedEvent, EventStage, EventStatus } from '@/types'

interface SSEPayload {
  stage?: EventStage
  message?: string
  status?: EventStatus
}

interface EventFeedHook {
  events: FeedEvent[]
  clearEvents: () => void
}

function buildEvent(payload: SSEPayload): FeedEvent {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    stage: payload.stage ?? 'system',
    message: payload.message ?? '',
    timestamp: new Date(),
    status: payload.status ?? 'running',
  }
}

export function useEventFeed(jobId: string | null): EventFeedHook {
  const [events, setEvents] = useState<FeedEvent[]>([])

  const clearEvents = useCallback(() => setEvents([]), [])

  useEffect(() => {
    if (!jobId) return

    const unsubscribe = subscribeSSE<SSEPayload>(`/api/jobs/${jobId}/stream`, {
      onMessage: (data) => {
        setEvents((prev) => [buildEvent(data), ...prev].slice(0, 200))
      },
      onError: () => {
        setEvents((prev) => [
          buildEvent({ stage: 'system', message: 'Stream disconnected', status: 'warning' }),
          ...prev,
        ])
      },
    })

    return unsubscribe
  }, [jobId])

  return { events, clearEvents }
}
