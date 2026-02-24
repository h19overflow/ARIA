import { Cpu, Terminal } from 'lucide-react'
import clsx from 'clsx'

export type TabId = 'build' | 'console'

interface Tab {
  id: TabId
  label: string
  icon: React.ReactNode
}

interface TabBarProps {
  active: TabId
  onChange: (tab: TabId) => void
}

const TABS: Tab[] = [
  { id: 'build', label: 'Build', icon: <Cpu size={15} /> },
  { id: 'console', label: 'Console', icon: <Terminal size={15} /> },
]

export function TabBar({ active, onChange }: TabBarProps) {
  return (
    <nav className="flex items-center gap-1 px-4 h-12 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      <div className="flex items-center gap-1 p-1 rounded-lg bg-[var(--bg-base)]">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={clsx(
              'flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-200',
              active === tab.id
                ? 'bg-[var(--accent-indigo)] text-white shadow-lg'
                : 'text-[var(--text-secondary)] hover:text-white hover:bg-white/5',
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>
      <div className="ml-auto flex items-center gap-2">
        <span className="text-xs font-mono text-[var(--text-muted)]">ARIA v0.1</span>
        <div className="w-2 h-2 rounded-full bg-[var(--color-success)] animate-pulse" />
      </div>
    </nav>
  )
}
