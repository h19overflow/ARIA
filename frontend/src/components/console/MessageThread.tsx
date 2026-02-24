import { Bot, User, Wrench, Monitor } from 'lucide-react'
import clsx from 'clsx'
import type { LangChainMessage, MessageRole } from '@/types'

interface MessageThreadProps {
  messages: LangChainMessage[] | undefined
}

interface RoleConfig {
  label: string
  icon: React.ReactNode
  bubbleClass: string
  nameClass: string
}

const ROLE_CONFIG: Record<MessageRole, RoleConfig> = {
  human: {
    label: 'You',
    icon: <User size={12} />,
    bubbleClass: 'bg-[var(--accent-indigo)]/20 border-[var(--accent-indigo)]/30 ml-8',
    nameClass: 'text-[var(--accent-indigo)]',
  },
  ai: {
    label: 'ARIA',
    icon: <Bot size={12} />,
    bubbleClass: 'bg-white/[0.03] border-[var(--border-subtle)] mr-8',
    nameClass: 'text-[var(--accent-violet)]',
  },
  system: {
    label: 'System',
    icon: <Monitor size={12} />,
    bubbleClass: 'bg-white/[0.02] border-[var(--border-subtle)] opacity-60',
    nameClass: 'text-[var(--text-muted)]',
  },
  tool: {
    label: 'Tool',
    icon: <Wrench size={12} />,
    bubbleClass: 'bg-[var(--color-warning)]/10 border-[var(--color-warning)]/20',
    nameClass: 'text-[var(--color-warning)]',
  },
}

function MessageBubble({ msg }: { msg: LangChainMessage }) {
  const config = ROLE_CONFIG[msg.type] ?? ROLE_CONFIG.system
  const content = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content, null, 2)

  return (
    <div className={clsx('border rounded-xl px-3 py-2.5', config.bubbleClass)}>
      <div className="flex items-center gap-1.5 mb-1">
        <span className={clsx('flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide', config.nameClass)}>
          {config.icon}
          {msg.name ?? config.label}
        </span>
      </div>
      <p className="text-xs text-[var(--text-secondary)] leading-relaxed whitespace-pre-wrap break-words">
        {content}
      </p>
    </div>
  )
}

export function MessageThread({ messages }: MessageThreadProps) {
  if (!messages || messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-[var(--text-muted)] text-sm">
        No messages yet
      </div>
    )
  }

  return (
    <div className="glass rounded-xl overflow-hidden">
      <div className="px-4 py-2.5 border-b border-[var(--border-subtle)]">
        <span className="text-xs font-semibold text-white">Message Thread</span>
        <span className="ml-2 text-[10px] text-[var(--text-muted)]">{messages.length} messages</span>
      </div>
      <div className="p-3 space-y-2 max-h-96 overflow-y-auto">
        {messages.map((msg, i) => (
          <MessageBubble key={msg.id ?? i} msg={msg} />
        ))}
      </div>
    </div>
  )
}
