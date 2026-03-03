import { useEffect } from "react";
import { BuildCanvas } from "@/components/build/BuildCanvas";
import { BuildEmptyState } from "@/components/build/BuildEmptyState";
import { BuildHeader } from "@/components/build/BuildHeader";
import { BuildSidebar } from "@/components/build/BuildSidebar";
import { SuccessBanner } from "@/components/build/SuccessBanner";
import { ClarifyDrawer } from "@/components/build/ClarifyDrawer";
import { CredentialDrawer } from "@/components/build/CredentialDrawer";
import { useBuild } from "@/hooks/useBuild";
import { PageGuide } from "@/components/shared/PageGuide";
import { BUILD_GUIDE } from "@/components/shared/guide-content";
interface BuildPageProps {
  conversationId: string;
}

export function BuildPage({ conversationId }: BuildPageProps) {
  const { state, start, resume, reset } = useBuild();
  const { status, ariaState, interrupt, events, error } = state;

  useEffect(() => {
    start(conversationId);
    return () => reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  const hasTopology = Boolean(
    ariaState?.workflow_json ||
    ariaState?.nodes_to_build?.length ||
    ariaState?.topology?.nodes?.length,
  );
  const isDone = status === "done";

  function handleClarifySubmit(answer: string) {
    resume("clarify", answer);
  }

  function handleCredentialSubmit(creds: Record<string, string>) {
    return resume("provide", creds);
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <BuildHeader status={status} ariaState={ariaState} />

      <div className="flex flex-1 overflow-hidden">
        {/* Main canvas */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          <div className="absolute top-3 left-3 right-3 z-10">
            <PageGuide
              title="How the build works"
              steps={BUILD_GUIDE}
              storageKey="guide-phase2"
            />
          </div>
          <div className="flex-1 overflow-hidden relative">
            {hasTopology ? (
              <BuildCanvas
                topology={ariaState?.topology ?? null}
                ariaState={ariaState}
                status={status}
                events={events}
              />
            ) : (
              <div className="w-full h-full bg-graph-grid">
                <BuildEmptyState
                  status={status}
                  error={error}
                  onRetry={() => start(conversationId)}
                />
              </div>
            )}

            {/* Clarify drawer — shown for mid-build clarification questions */}
            {interrupt?.kind === "clarify" && (
              <ClarifyDrawer
                question={interrupt.payload.question ?? ""}
                onSubmit={handleClarifySubmit}
                isLoading={false}
              />
            )}

            {/* Success banner overlaid at bottom of canvas */}
            {isDone && (
              <SuccessBanner
                n8nWorkflowUrl={ariaState?.n8n_workflow_url}
              />
            )}
          </div>

          {/* Credential drawer below canvas */}
          {interrupt?.kind === "credential" && (
            <CredentialDrawer
              pendingTypes={(interrupt.payload.pending_types as string[]) ?? []}
              guide={ariaState?.credential_guide_payload}
              onSubmit={
                handleCredentialSubmit as (
                  creds: Record<string, string>,
                ) => Promise<void>
              }
            />
          )}
        </div>

        <BuildSidebar ariaState={ariaState} status={status} events={events} />
      </div>
    </div>
  );
}
