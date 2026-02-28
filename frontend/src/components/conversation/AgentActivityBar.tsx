import { useEffect, useRef } from 'react';
import { Loader2, CheckCircle2, Pencil, Send, KeyRound } from 'lucide-react';
import type { AgentActivity } from '@/types';

interface AgentActivityBarProps {
  activities: AgentActivity[];
  isStreaming: boolean;
}

function formatToolLabel(tool: string, args?: Record<string, unknown>): string {
  if (tool === 'take_note') {
    const key = args?.key as string | undefined;
    const value = args?.value as string | undefined;
    if (key && value) {
      const truncated = value.length > 40 ? value.slice(0, 40) + '...' : value;
      return `Noting ${key}: "${truncated}"`;
    }
    if (key) return `Clearing ${key}`;
    return 'Taking note';
  }
  if (tool === 'batch_notes') {
    const notes = args?.notes as unknown[] | undefined;
    return `Recording ${notes?.length ?? ''} notes`;
  }
  if (tool === 'commit_notes') return 'Committing requirements';
  if (tool === 'scan_credentials') return 'Scanning credentials';
  if (tool === 'get_credential_schema') {
    const credType = args?.credential_type as string | undefined;
    return credType ? `Fetching ${credType} schema` : 'Fetching credential schema';
  }
  if (tool === 'save_credential') {
    const name = args?.name as string | undefined;
    return name ? `Saving ${name}` : 'Saving credential';
  }
  if (tool === 'commit_preflight') return 'Finalizing credentials';
  return `Calling ${tool}`;
}

const CREDENTIAL_TOOLS = new Set(['scan_credentials', 'save_credential', 'get_credential_schema', 'commit_preflight']);

function ToolIcon({ tool }: { tool: string }) {
  if (tool === 'commit_notes') return <Send size={11} style={{ flexShrink: 0, opacity: 0.7 }} />;
  if (CREDENTIAL_TOOLS.has(tool)) return <KeyRound size={11} style={{ flexShrink: 0, opacity: 0.7 }} />;
  return <Pencil size={11} style={{ flexShrink: 0, opacity: 0.7 }} />;
}

function ActivityChip({ activity, isComplete }: { activity: AgentActivity; isComplete: boolean }) {
  return (
    <div className="activity-chip" style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      padding: '3px 10px', borderRadius: '12px', flexShrink: 0,
      fontSize: '0.72rem', lineHeight: 1,
      background: isComplete ? 'rgba(52,211,153,0.1)' : 'var(--accent-orange-dim)',
      border: `1px solid ${isComplete ? 'rgba(52,211,153,0.25)' : 'rgba(238,79,39,0.25)'}`,
      color: isComplete ? 'var(--color-success)' : 'var(--accent-orange)',
      animation: 'fadeSlideIn 200ms ease-out',
    }}>
      {isComplete
        ? <CheckCircle2 size={11} style={{ flexShrink: 0 }} />
        : <Loader2 size={11} className="animate-spin" style={{ flexShrink: 0 }} />}
      <ToolIcon tool={activity.tool} />
      <span style={{ whiteSpace: 'nowrap' }}>
        {formatToolLabel(activity.tool, activity.args)}
      </span>
    </div>
  );
}

function ThinkingChip() {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      padding: '3px 10px', borderRadius: '12px', flexShrink: 0,
      fontSize: '0.72rem',
      background: 'rgba(255,255,255,0.04)',
      border: '1px solid rgba(255,255,255,0.08)',
      color: 'var(--text-secondary)',
    }}>
      <Loader2 size={11} className="animate-spin" />
      <span>Thinking...</span>
    </div>
  );
}

export function AgentActivityBar({ activities, isStreaming }: AgentActivityBarProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ left: scrollRef.current.scrollWidth, behavior: 'smooth' });
  }, [activities]);

  if (!isStreaming && activities.length === 0) return null;

  const recent = activities.slice(-6);
  const lastActivity = activities[activities.length - 1];
  const isToolRunning = lastActivity?.type === 'tool_start';

  return (
    <div style={{
      padding: '6px 24px',
      borderTop: '1px solid rgba(238,79,39,0.15)',
      background: 'linear-gradient(180deg, rgba(238,79,39,0.04) 0%, transparent 100%)',
      maxWidth: '680px', width: '100%',
      marginInline: 'auto', boxSizing: 'border-box',
    }}>
      <div ref={scrollRef} style={{
        display: 'flex', gap: '6px', overflowX: 'auto', alignItems: 'center',
        scrollbarWidth: 'none',
      }}>
        <span style={{
          fontSize: '0.6rem', fontWeight: 700, letterSpacing: '0.1em',
          textTransform: 'uppercase', color: 'var(--text-muted)',
          flexShrink: 0, marginRight: '4px',
        }}>
          Agent
        </span>

        {recent.map(activity => {
          if (activity.type === 'tool_end') return null;
          const hasEnd = activities.some(
            a => a.type === 'tool_end' && a.tool === activity.tool && a.timestamp > activity.timestamp,
          );
          return (
            <ActivityChip
              key={activity.id}
              activity={activity}
              isComplete={hasEnd}
            />
          );
        })}

        {isStreaming && !isToolRunning && <ThinkingChip />}
      </div>
    </div>
  );
}
