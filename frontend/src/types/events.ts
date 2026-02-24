export type EventStage = 'preflight' | 'build' | 'test' | 'fix' | 'system'
export type EventStatus = 'running' | 'success' | 'error' | 'warning'

export interface FeedEvent {
  id: string
  stage: EventStage
  message: string
  timestamp: Date
  status: EventStatus
}
