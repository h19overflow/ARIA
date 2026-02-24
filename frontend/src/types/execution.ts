export interface ExecutionResult {
  status: 'success' | 'error' | 'unknown'
  execution_id?: string
  data?: unknown
  error?: string
}

export interface ClassifiedError {
  type: string
  node_name: string
  message: string
  description: string
  line_number?: number | null
  stack?: string | null
}
