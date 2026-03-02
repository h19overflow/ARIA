import { useState } from "react";
import { MessageCircle, Send, Loader2 } from "lucide-react";
import clsx from "clsx";

interface ClarifyDrawerProps {
  question: string;
  onSubmit: (answer: string) => void;
  isLoading: boolean;
}

export function ClarifyDrawer({
  question,
  onSubmit,
  isLoading,
}: ClarifyDrawerProps) {
  const [answer, setAnswer] = useState("");

  function handleSubmit() {
    const trimmed = answer.trim();
    if (!trimmed || isLoading) return;
    onSubmit(trimmed);
    setAnswer("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleSubmit();
  }

  return (
    <div className="absolute inset-x-0 bottom-0 z-20 p-4 animate-slide-in">
      <div className="rounded-xl border border-[var(--accent-indigo)]/30 bg-slate-900/60 backdrop-blur-md shadow-2xl shadow-indigo-500/10 p-4 space-y-3">
        <div className="flex items-start gap-3">
          <div className="w-7 h-7 rounded-lg bg-[var(--accent-indigo)]/15 flex items-center justify-center flex-none mt-0.5">
            <MessageCircle size={14} className="text-[var(--accent-indigo)]" />
          </div>
          <div>
            <p className="text-xs font-semibold text-[var(--accent-indigo)] uppercase tracking-wide mb-1">
              Clarification needed
            </p>
            <p className="text-sm text-white leading-relaxed">{question}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <input
            autoFocus
            type="text"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="Type your answer…"
            className={clsx(
              "flex-1 bg-[var(--bg-surface)] border border-[var(--border-muted)] rounded-lg px-3 py-2",
              "text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none",
              "focus:border-[var(--accent-indigo)]/60 transition-colors duration-150",
              isLoading && "opacity-50 cursor-not-allowed",
            )}
          />
          <button
            onClick={handleSubmit}
            disabled={!answer.trim() || isLoading}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold",
              "bg-[var(--accent-indigo)] text-white transition-all duration-150",
              "hover:bg-indigo-500 active:scale-95",
              "disabled:opacity-40 disabled:cursor-not-allowed disabled:scale-100",
            )}
          >
            {isLoading ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
