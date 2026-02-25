import clsx from 'clsx'
import { Workflow } from 'lucide-react'

interface NodeChipsProps {
  nodes: string[]
}

const NODE_ICONS: Record<string, string> = {
  webhook: '⚡',
  gmail: '✉',
  email: '✉',
  sheets: '📊',
  spreadsheet: '📊',
  slack: '💬',
  discord: '💬',
  http: '🌐',
  request: '🌐',
  code: '⚙',
  function: '⚙',
  schedule: '🕒',
  cron: '🕒',
  notion: '📝',
  airtable: '📊',
  github: '🐙',
  postgres: '🗄',
  mysql: '🗄',
  openai: '🤖',
  anthropic: '🤖',
  default: '◆',
}

function getIcon(node: string): string {
  const lower = node.toLowerCase()
  for (const [key, icon] of Object.entries(NODE_ICONS)) {
    if (lower.includes(key)) return icon
  }
  return NODE_ICONS.default
}

function cleanNodeName(raw: string): string {
  return raw
    .replace(/n8n-nodes-base\./i, '')
    .replace(/([A-Z])/g, ' $1')
    .replace(/\s+/g, ' ')
    .trim()
}

export function NodeChips({ nodes }: NodeChipsProps) {
  if (nodes.length === 0) {
    return (
      <div className="rounded-xl border border-white/8 bg-white/[0.02] p-4">
        <div className="flex items-center gap-2 mb-3">
          <Workflow size={14} className="text-white/40" />
          <span className="text-xs font-mono font-semibold text-white/40 uppercase tracking-widest">
            Steps in your workflow
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {[80, 60, 96, 72].map((w, i) => (
            <div key={i} className={clsx('skeleton h-7 rounded-full')} style={{ width: w }} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.02] p-4">
      <div className="flex items-center gap-2 mb-3">
        <Workflow size={14} className="text-white/40" />
        <span className="text-xs font-mono font-semibold text-white/40 uppercase tracking-widest">
          Steps in your workflow
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {nodes.map((node, i) => (
          <span
            key={node}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/6 border border-white/10 text-xs text-white/65 animate-node-appear"
            style={{ animationDelay: `${i * 60}ms`, animationFillMode: 'both' }}
          >
            <span>{getIcon(node)}</span>
            <span>{cleanNodeName(node)}</span>
          </span>
        ))}
      </div>
    </div>
  )
}
