import { Cpu, Terminal, CheckCircle2, Circle, Loader2, XCircle, Zap } from 'lucide-react'
import clsx from 'clsx'
import type { WorkflowStatus } from '@/types'

export type TabId = 'build' | 'console'

interface SidebarProps {
  active: TabId
  onChange: (tab: TabId) => void
  status: WorkflowStatus
  buildPhase?: number
  totalPhases?: number
}

interface NavItem {
  id: TabId
  label: string
  icon: React.ReactNode
}

const NAV: NavItem[] = [
  { id: 'build', label: 'Build', icon: <Cpu size={16} /> },
  { id: 'console', label: 'Console', icon: <Terminal size={16} /> },
]

interface Stage {
  id: string
  label: string
  statuses: WorkflowStatus[]
}

const STAGES: Stage[] = [
  { id: 'preflight', label: 'Preflight', statuses: ['planning'] },
  { id: 'orchestrate', label: 'Orchestrate', statuses: ['replanning'] },
  { id: 'build', label: 'Build', statuses: ['building'] },
  { id: 'test', label: 'Test', statuses: ['testing', 'fixing'] },
  { id: 'done', label: 'Done', statuses: ['done'] },
]

const STATUS_ORDER = ['planning', 'replanning', 'building', 'testing', 'fixing', 'done', 'failed']

function getStageState(stage: Stage, current: WorkflowStatus): 'idle' | 'active' | 'done' | 'error' {
  if (current === 'idle') return 'idle'
  if (current === 'failed') {
    const ci = STATUS_ORDER.indexOf(current)
    const si = Math.min(...stage.statuses.map((s) => STATUS_ORDER.indexOf(s)))
    return si < ci ? 'done' : 'error'
  }
  if (stage.statuses.includes(current)) return 'active'
  const ci = STATUS_ORDER.indexOf(current)
  const si = Math.min(...stage.statuses.map((s) => STATUS_ORDER.indexOf(s)))
  return si < ci ? 'done' : 'idle'
}

function StageIcon({ state }: { state: ReturnType<typeof getStageState> }) {
  if (state === 'done') return <CheckCircle2 size={13} className="text-[var(--color-success)] flex-none" />
  if (state === 'error') return <XCircle size={13} className="text-[var(--color-error)] flex-none" />
  if (state === 'active') return <Loader2 size={13} className="text-[var(--accent-indigo)] animate-spin flex-none" />
  return <Circle size={13} className="text-[var(--text-muted)] flex-none" />
}

export function Sidebar({ active, onChange, status, buildPhase, totalPhases }: SidebarProps) {
  const showPipeline = status !== 'idle'

  return (
    <aside className="w-52 flex-none flex flex-col h-full border-r border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-14 border-b border-[var(--border-subtle)]">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--accent-indigo)] to-[var(--accent-violet)] flex items-center justify-center shadow-lg shadow-indigo-500/30 flex-none">
          <Zap size={15} className="text-white" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-bold text-white tracking-tight leading-none">ARIA</p>
          <p className="text-[10px] text-[var(--text-muted)] mt-0.5 truncate">Workflow Automator</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="px-2 pt-3 space-y-0.5">
        <p className="px-2 pb-1.5 text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-widest">
          Navigation
        </p>
        {NAV.map((item) => (
          <button
            key={item.id}
            onClick={() => onChange(item.id)}
            className={clsx(
              'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150',
              active === item.id
                ? 'bg-[var(--accent-indigo)]/15 text-[var(--accent-indigo)] border border-[var(--accent-indigo)]/20'
                : 'text-[var(--text-secondary)] hover:text-white hover:bg-white/5 border border-transparent',
            )}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </nav>

      {/* Pipeline stages */}
      {showPipeline && (
        <div className="px-2 pt-5">
          <p className="px-2 pb-2 text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-widest">
            Pipeline
          </p>
          <div className="relative pl-3">
            {/* Vertical connector line */}
            <div className="absolute left-[22px] top-2 bottom-2 w-px bg-[var(--border-subtle)]" />
            <div className="space-y-0.5">
              {STAGES.map((stage) => {
                const state = getStageState(stage, status)
                const isActive = state === 'active'
                return (
                  <div
                    key={stage.id}
                    className={clsx(
                      'flex items-center gap-2.5 px-2 py-1.5 rounded-lg transition-all duration-200',
                      isActive && 'bg-[var(--accent-indigo)]/8',
                    )}
                  >
                    <StageIcon state={state} />
                    <span
                      className={clsx('text-xs font-medium transition-colors duration-200', {
                        'text-white': isActive,
                        'text-[var(--color-success)]': state === 'done',
                        'text-[var(--color-error)]': state === 'error',
                        'text-[var(--text-muted)]': state === 'idle',
                      })}
                    >
                      {stage.label}
                      {isActive && stage.id === 'build' && buildPhase && totalPhases
                        ? ` ${buildPhase}/${totalPhases}`
                        : ''}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-auto px-4 py-3 border-t border-[var(--border-subtle)]">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono text-[var(--text-muted)]">v0.1.0</span>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)] animate-pulse" />
            <span className="text-[10px] text-[var(--text-muted)]">Online</span>
          </div>
        </div>
      </div>
    </aside>
  )
}
