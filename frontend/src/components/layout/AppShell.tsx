import { useState } from 'react'
import { TabBar, type TabId } from './TabBar'
import { BuildPage } from '@/pages/BuildPage'
import { ConsolePage } from '@/pages/ConsolePage'
import { useWorkflow } from '@/hooks/useWorkflow'
import { useEventFeed } from '@/hooks/useEventFeed'

export function AppShell() {
  const [activeTab, setActiveTab] = useState<TabId>('build')
  const workflow = useWorkflow()
  const feed = useEventFeed(workflow.jobId)

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-[var(--bg-base)]">
      <header className="flex-none flex items-center gap-3 px-4 h-14 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[var(--accent-indigo)] to-[var(--accent-violet)] flex items-center justify-center">
            <span className="text-white text-xs font-bold">A</span>
          </div>
          <span className="text-sm font-semibold text-white tracking-wide">ARIA</span>
          <span className="text-[var(--text-muted)] text-xs">AI Workflow Automator</span>
        </div>
      </header>

      <TabBar active={activeTab} onChange={setActiveTab} />

      <main className="flex-1 overflow-hidden">
        {activeTab === 'build' && (
          <BuildPage workflow={workflow} feed={feed} />
        )}
        {activeTab === 'console' && (
          <ConsolePage ariaState={workflow.ariaState} />
        )}
      </main>
    </div>
  )
}
