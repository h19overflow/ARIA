import { useRef, useEffect, useState, KeyboardEvent } from 'react';
import { Send, Loader2, Play, Bot, Zap, RefreshCw, BookOpen } from 'lucide-react';
import type { Message } from '../../hooks/useConversation';

interface ChatPanelProps {
  messages: Message[];
  isStreaming: boolean;
  isCommitted: boolean;
  error: string | null;
  workflowError?: string | null;
  isStarting?: boolean;
  onSendMessage: (content: string) => Promise<void>;
  onStartBuilding: () => Promise<void>;
}

const SUGGESTIONS = [
  { icon: <Zap size={13} />, label: 'Monitor GitHub PRs' },
  { icon: <RefreshCw size={13} />, label: 'Sync Slack → Notion' },
  { icon: <BookOpen size={13} />, label: 'Send daily digest' },
];

// Max width of the content column — same feel as Claude web
const COL = '720px';

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', gap: '4px', padding: '4px 0', alignItems: 'center' }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: '6px', height: '6px', borderRadius: '50%',
            background: 'var(--accent-indigo)', display: 'inline-block',
            animation: `typingBounce 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
    </div>
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user';
  return (
    <div style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
      {isUser ? (
        <div style={{
          maxWidth: '80%', padding: '10px 15px',
          borderRadius: '18px 18px 4px 18px',
          background: 'linear-gradient(135deg, var(--accent-indigo), var(--accent-violet))',
          color: '#fff', fontSize: '0.9rem', lineHeight: 1.6, whiteSpace: 'pre-wrap',
        }}>
          {msg.content}
        </div>
      ) : (
        <div style={{
          maxWidth: '100%', fontSize: '0.9rem', lineHeight: 1.7,
          color: 'var(--text-primary)', whiteSpace: 'pre-wrap',
        }}>
          {msg.content}
        </div>
      )}
    </div>
  );
}

export function ChatPanel({ messages, isStreaming, isCommitted, error, workflowError, isStarting, onSendMessage, onStartBuilding }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

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
    textareaRef.current?.focus();
    await onSendMessage(trimmed);
  };

  const hasMessages = messages.length > 0 || isStreaming;

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0, position: 'relative' }}>

      {/* Top bar — only "Start Building" when committed */}
      {isCommitted && (
        <div style={{ position: 'absolute', top: 16, right: 20, zIndex: 10 }}>
          <button
            onClick={onStartBuilding}
            disabled={isStarting}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '8px 16px',
              background: isStarting ? 'var(--bg-elevated)' : 'linear-gradient(135deg, var(--accent-indigo), var(--accent-violet))',
              border: 'none', borderRadius: '8px', color: '#fff',
              fontWeight: 600, fontSize: '0.82rem',
              cursor: isStarting ? 'not-allowed' : 'pointer',
              boxShadow: isStarting ? 'none' : '0 0 20px rgba(99,102,241,0.45)',
              transition: 'all 150ms ease',
              opacity: isStarting ? 0.6 : 1,
            }}
          >
            {isStarting ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            Start Building
          </button>
        </div>
      )}

      {/* Scrollable message area */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>

        {/* Empty / welcome state — vertically centered */}
        {!hasMessages && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 24px', gap: '24px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
              <Bot size={36} style={{ color: 'var(--accent-indigo)', opacity: 0.7 }} />
              <p style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>What would you like to automate?</p>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>Describe a workflow and ARIA will build it for you.</p>
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.label}
                  onClick={() => { setInput(s.label); textareaRef.current?.focus(); }}
                  className="glass"
                  style={{
                    display: 'flex', alignItems: 'center', gap: '6px',
                    padding: '8px 14px', borderRadius: '8px',
                    fontSize: '0.8rem', color: 'var(--text-secondary)',
                    cursor: 'pointer', border: '1px solid var(--border-muted)',
                    background: 'var(--bg-elevated)',
                    transition: 'transform 150ms ease, border-color 150ms ease',
                  }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; (e.currentTarget as HTMLElement).style.borderColor = 'var(--accent-indigo)'; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.transform = 'none'; (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-muted)'; }}
                >
                  <span style={{ color: 'var(--accent-indigo)' }}>{s.icon}</span>
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message thread */}
        {hasMessages && (
          <div style={{ flex: 1, padding: '32px 24px 16px', display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: COL, width: '100%', marginInline: 'auto', boxSizing: 'border-box' }}>
            {messages.map((msg) => <MessageBubble key={msg.id} msg={msg} />)}
            {isStreaming && messages[messages.length - 1]?.role !== 'assistant' && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}
        {!hasMessages && <div ref={bottomRef} />}
      </div>

      {/* Input area — centered column with padding, floats above bottom */}
      <div style={{ flexShrink: 0, padding: '12px 24px 28px', maxWidth: COL, width: '100%', marginInline: 'auto', boxSizing: 'border-box' }}>
        {(error || workflowError) && (
          <p style={{ fontSize: '0.75rem', color: 'var(--color-error)', marginBottom: '8px' }}>
            {error || workflowError}
          </p>
        )}
        <div
          style={{
            display: 'flex', alignItems: 'flex-end', gap: '10px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-muted)',
            borderRadius: '14px',
            padding: '12px 14px',
            boxShadow: '0 4px 24px rgba(0,0,0,0.35)',
            transition: 'border-color 150ms ease',
          }}
          onFocusCapture={(e) => (e.currentTarget as HTMLElement).style.borderColor = 'rgba(99,102,241,0.5)'}
          onBlurCapture={(e) => (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-muted)'}
        >
          <textarea
            ref={textareaRef}
            value={input}
            rows={1}
            disabled={isStreaming}
            onChange={(e) => { setInput(e.target.value); resizeTextarea(); }}
            onKeyDown={handleKeyDown}
            placeholder="Describe your workflow..."
            style={{
              flex: 1, resize: 'none', background: 'transparent',
              border: 'none', outline: 'none',
              fontSize: '0.9rem', color: 'var(--text-primary)',
              lineHeight: 1.6, overflow: 'hidden', maxHeight: '160px',
              fontFamily: 'Inter, sans-serif',
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            aria-label="Send message"
            style={{
              flexShrink: 0, width: '34px', height: '34px', borderRadius: '8px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: input.trim() && !isStreaming ? 'var(--accent-indigo)' : 'rgba(255,255,255,0.06)',
              color: input.trim() && !isStreaming ? '#fff' : 'var(--text-muted)',
              border: 'none',
              cursor: input.trim() && !isStreaming ? 'pointer' : 'default',
              transition: 'background 150ms ease, color 150ms ease',
            }}
          >
            {isStreaming ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
          </button>
        </div>
        <p style={{ textAlign: 'center', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '8px', margin: '8px 0 0' }}>
          Enter to send · Shift+Enter for newline
        </p>
      </div>

    </div>
  );
}
