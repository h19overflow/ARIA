import { useState, useEffect } from 'react'
import { Sidebar, type TabId } from './Sidebar'
import { BuildPage } from '@/pages/BuildPage'
import { ConsolePage } from '@/pages/ConsolePage'
import { useWorkflow } from '@/hooks/useWorkflow'
import { ConversationView } from '@/views/ConversationView'

export type ViewMode = 'conversation' | 'studio'

export function AppShell() {
  const [viewMode, setViewMode] = useState<ViewMode>('conversation')
  const [activeTab, setActiveTab] = useState<TabId>('build')
  const workflow = useWorkflow()

  // Handle view transitions based on workflow state
  useEffect(() => {
    if (workflow.jobId && viewMode === 'conversation') {
      setViewMode('studio')
    } else if (workflow.status === 'idle' && viewMode === 'studio') {
      setViewMode('conversation')
    }
  }, [workflow.jobId, workflow.status, viewMode])

  const handleStartBuilding = async (conversationId: string) => {
    await workflow.startFromConversation(conversationId)
  }

  if (viewMode === 'conversation') {
    return (
      <div className="flex h-screen overflow-hidden bg-[var(--bg-base)]">
        <ConversationView 
          onStartBuilding={handleStartBuilding}
          isStarting={workflow.isLoading}
          workflowError={workflow.error}
        />
      </div>
    )
  }

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
