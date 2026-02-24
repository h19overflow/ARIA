export interface SSEHandlers<T> {
  onMessage: (data: T) => void
  onError?: (err: Event) => void
  onOpen?: () => void
}

/**
 * Subscribe to a server-sent events endpoint.
 * Returns an unsubscribe function that closes the connection.
 */
export function subscribeSSE<T>(
  url: string,
  handlers: SSEHandlers<T>,
): () => void {
  const source = new EventSource(url)

  source.onopen = () => handlers.onOpen?.()

  source.onmessage = (event: MessageEvent<string>) => {
    try {
      const parsed = JSON.parse(event.data) as T
      handlers.onMessage(parsed)
    } catch {
      // non-JSON keep-alive lines — ignore
    }
  }

  source.onerror = (err) => {
    handlers.onError?.(err)
    source.close()
  }

  return () => source.close()
}
