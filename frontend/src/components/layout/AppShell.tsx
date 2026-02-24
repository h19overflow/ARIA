import { useState } from 'react'
import { Sidebar, type TabId } from './Sidebar'
import { BuildPage } from '@/pages/BuildPage'
import { ConsolePage } from '@/pages/ConsolePage'
import { useWorkflow } from '@/hooks/useWorkflow'

export function AppShell() {
  const [activeTab, setActiveTab] = useState<TabId>('build')
  const workflow = useWorkflow()

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-base)]">
      <Sidebar
        active={activeTab}
        onChange={setActiveTab}
        status={workflow.status}
        buildPhase={workflow.ariaState?.build_phase}
        totalPhases={workflow.ariaState?.total_phases}
      />
      <main className="flex-1 overflow-hidden">
        {activeTab === 'build' && <BuildPage workflow={workflow} />}
        {activeTab === 'console' && <ConsolePage ariaState={workflow.ariaState} />}
      </main>
    </div>
  )
}
