export type MessageRole = 'human' | 'ai' | 'system' | 'tool'

export interface LangChainMessage {
  type: MessageRole
  content: string
  id?: string
  name?: string
}
