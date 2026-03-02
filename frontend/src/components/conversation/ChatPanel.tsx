import { useRef, useEffect, useState, KeyboardEvent } from 'react';
import { Send, Loader2, Zap, RefreshCw, BookOpen, CheckCircle2 } from 'lucide-react';
import { clsx } from 'clsx';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '@/store';
import type { AgentActivity } from '@/types';
import { AgentActivityBar } from './AgentActivityBar';

interface ChatPanelProps {
  messages: Message[];
  activities: AgentActivity[];
  isStreaming: boolean;
  isCommitted: boolean;
  error: string | null;
  workflowError?: string | null;
  isStarting?: boolean;
  onSendMessage: (content: string) => Promise<void>;
}

const COL = '680px';

const SUGGESTIONS = [
  {
    icon: Zap,
    label: 'Gmail → AI → Telegram',
    sub: 'Summarize new emails and send to Telegram',
    prompt: 'When I receive an email in Gmail, summarize it with AI and send the summary to my Telegram chat. Only process unread emails, keep summaries under 200 words.',
  },
  {
    icon: RefreshCw,
    label: 'GitHub → Slack alerts',
    sub: 'Get Slack notifications on new PRs',
    prompt: 'Monitor my GitHub repository for new pull requests. When a new PR is opened, send a formatted Slack message with the PR title, author, and link.',
  },
  {
    icon: BookOpen,
    label: 'Daily email digest',
    sub: 'Summarize RSS feeds every morning',
    prompt: 'Every day at 8 AM, fetch the latest articles from an RSS feed, summarize the top 5 with AI, and send me a digest email with the summaries and links.',
  },
];

function TypingDots() {
  return (
    <div style={{ display: 'flex', gap: '4px', padding: '2px 0', alignItems: 'center' }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: 'var(--accent-orange)', display: 'inline-block',
          animation: `typingBounce 1.2s ease-in-out ${i * 0.2}s infinite`,
        }} />
      ))}
    </div>
  );
}

function UserBubble({ content }: { content: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end' }} className="msg-enter">
      <div style={{
        maxWidth: '78%', padding: '10px 15px',
        borderRadius: '18px 18px 4px 18px',
        background: 'linear-gradient(135deg, #ee4f27, #c93d1b)',
        color: '#fff', fontSize: '0.875rem', lineHeight: 1.6, whiteSpace: 'pre-wrap',
        boxShadow: '0 2px 12px rgba(238,79,39,0.3)',
      }}>
        {content}
      </div>
    </div>
  );
}

function AiBubble({ content }: { content: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-start' }} className="msg-enter">
      <div className="prose-aria" style={{
        maxWidth: '92%', fontSize: '0.875rem', lineHeight: 1.75,
        color: 'var(--text-primary)',
        borderLeft: '2px solid rgba(238,79,39,0.3)', paddingLeft: '14px',
      }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    </div>
  );
}

export function ChatPanel({ messages, activities, isStreaming, isCommitted, error, workflowError, isStarting: _isStarting, onSendMessage }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isStreaming]);

  const prevStreamingRef = useRef(false);
  useEffect(() => {
    if (prevStreamingRef.current && !isStreaming) {
      textareaRef.current?.focus();
    }
    prevStreamingRef.current = isStreaming;
  }, [isStreaming]);

  const resizeTextarea = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    await onSendMessage(trimmed);
  };

  const hasMessages = messages.length > 0 || isStreaming;

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>

      {/* Scrollable messages */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>

        {/* Empty state */}
        {!hasMessages && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 24px', gap: '32px' }}>
            <div style={{ textAlign: 'center' }}>
              <p style={{ fontSize: '1.35rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                What would you like to automate?
              </p>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Describe it in plain language — I'll ask a few questions, then build it.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', justifyContent: 'center', maxWidth: '560px' }}>
              {SUGGESTIONS.map(s => (
                <button key={s.label} className="suggestion-card"
                  style={{ width: '160px' }}
                  onClick={() => { setInput(s.prompt); textareaRef.current?.focus(); }}>
                  <s.icon size={15} style={{ color: 'var(--accent-orange)' }} />
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>{s.label}</span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>{s.sub}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {hasMessages && (
          <div style={{ flex: 1, padding: '28px 24px 16px', display: 'flex', flexDirection: 'column', gap: '18px', maxWidth: COL, width: '100%', marginInline: 'auto', boxSizing: 'border-box' }}>
            {messages.map(msg =>
              msg.role === 'user'
                ? <UserBubble key={msg.id} content={msg.content} />
                : <AiBubble key={msg.id} content={msg.content} />
            )}
            {isStreaming && messages[messages.length - 1]?.role !== 'assistant' && (
              <div style={{ paddingLeft: '16px' }}><TypingDots /></div>
            )}
            {isCommitted && (
              <div className="committed-banner" style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                padding: '10px 14px', borderRadius: '10px',
                background: 'rgba(238,79,39,0.08)', border: '1px solid rgba(238,79,39,0.25)',
              }}>
                <CheckCircle2 size={15} style={{ color: 'var(--accent-orange)', flexShrink: 0 }} />
                <span style={{ fontSize: '0.82rem', color: 'var(--accent-orange)', fontWeight: 500 }}>
                  Requirements captured — once credentials are resolved, click "Start Build" in the sidebar.
                </span>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
        {!hasMessages && <div ref={bottomRef} />}
      </div>

      {/* Agent Activity Bar - between messages and input */}
      <AgentActivityBar activities={activities} isStreaming={isStreaming} />

      {/* Input area */}
      <div style={{ flexShrink: 0, padding: '10px 24px 24px', maxWidth: COL, width: '100%', marginInline: 'auto', boxSizing: 'border-box' }}>
        {(error || workflowError) && (
          <p style={{ fontSize: '0.75rem', color: 'var(--color-error)', marginBottom: '8px' }}>
            {error || workflowError}
          </p>
        )}
        <div className={clsx('input-focus-orange')} style={{
          display: 'flex', alignItems: 'center', gap: '10px',
          background: 'var(--bg-elevated)', border: '1px solid var(--border-muted)',
          borderRadius: '14px', padding: '12px 14px',
          boxShadow: '0 4px 24px rgba(0,0,0,0.35)',
          transition: 'border-color 150ms ease',
        }}>
          <textarea
            ref={textareaRef}
            value={input}
            rows={1}
            disabled={isStreaming}
            onChange={e => { setInput(e.target.value); resizeTextarea(); }}
            onKeyDown={handleKeyDown}
            placeholder="Tell me what you want to automate..."
            style={{
              flex: 1, resize: 'none', background: 'transparent',
              border: 'none', outline: 'none',
              fontSize: '0.9rem', color: 'var(--text-primary)',
              lineHeight: 1.6, overflow: 'hidden', maxHeight: '160px',
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            aria-label="Send message"
            style={{
              flexShrink: 0, width: '34px', height: '34px', borderRadius: '8px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: input.trim() && !isStreaming ? 'var(--accent-orange)' : 'rgba(255,255,255,0.06)',
              color: input.trim() && !isStreaming ? '#fff' : 'var(--text-muted)',
              border: 'none', cursor: input.trim() && !isStreaming ? 'pointer' : 'default',
              transition: 'background 150ms ease, color 150ms ease',
            }}
          >
            {isStreaming ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
          </button>
        </div>
        <p style={{ textAlign: 'center', fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '8px' }}>
          Enter to send · Shift+Enter for newline
        </p>
      </div>
    </div>
  );
}
