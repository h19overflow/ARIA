import clsx from 'clsx'
import { ArrowRight } from 'lucide-react'
import type { ARIAState, WorkflowStatus } from '@/types'
import { IntentCard } from './IntentCard'
import { CredentialChecklist } from './CredentialChecklist'
import { NodeChips } from './NodeChips'

interface BlueprintPanelProps {
  ariaState: ARIAState | null
  status: WorkflowStatus
  onStartBuild: () => void
  onConnectMissing?: () => void
}

export function BlueprintPanel({ ariaState, status, onStartBuild, onConnectMissing }: BlueprintPanelProps) {
  const isComplete = status === 'done' && ariaState?.build_blueprint != null
  const nodes = ariaState?.required_nodes ?? []
  const hasMissing = (ariaState?.pending_credential_types ?? []).length > 0

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      <div className="max-w-2xl mx-auto flex flex-col gap-4">
        <IntentCard ariaState={ariaState} />
        <CredentialChecklist ariaState={ariaState} onConnectMissing={hasMissing ? onConnectMissing : undefined} />
        <NodeChips nodes={nodes} />

        {/* Start build button */}
        <div
          className={clsx(
            'transition-all duration-500',
            isComplete ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2 pointer-events-none',
          )}
        >
          <button
            onClick={onStartBuild}
            disabled={!isComplete}
            className={clsx(
              'w-full flex items-center justify-center gap-3 py-3.5 rounded-xl',
              'font-semibold text-sm text-white transition-all duration-200',
              'bg-phase2 hover:bg-phase2/90 shadow-glow-green hover:shadow-lg',
              'disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none',
              isComplete && 'hover:-translate-y-0.5',
            )}
          >
            <span>Start Building</span>
            <ArrowRight size={16} strokeWidth={2.5} />
          </button>
        </div>
      </div>
    </div>
  )
}
