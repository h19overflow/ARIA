import { useState } from "react";
import { KeyRound, X, Send } from "lucide-react";
import clsx from "clsx";
import type { CredentialGuidePayload } from "@/types";

interface CredentialDrawerProps {
  pendingTypes: string[];
  guide: CredentialGuidePayload | undefined;
  onSubmit: (creds: Record<string, string>) => Promise<void>;
}

function getFirstEntry(guide: CredentialGuidePayload | undefined) {
  return guide?.entries?.[0];
}

function buildInitialValues(
  guide: CredentialGuidePayload | undefined,
  types: string[],
): Record<string, string> {
  const entry = getFirstEntry(guide);
  if (entry) return Object.fromEntries(entry.fields.map((f) => [f.name, ""]));
  return Object.fromEntries(types.map((t) => [t, ""]));
}

export function CredentialDrawer({
  pendingTypes,
  guide,
  onSubmit,
}: CredentialDrawerProps) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    buildInitialValues(guide, pendingTypes),
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (pendingTypes.length === 0) return null;

  const entry = getFirstEntry(guide);
  const fields =
    entry?.fields?.map((f) => ({
      name: f.name,
      label: f.label,
      type: (f.type ?? "password") as "text" | "password" | "url",
      placeholder: f.placeholder ?? `Enter ${f.label}`,
    })) ??
    pendingTypes.map((t) => ({
      name: t,
      label: t,
      type: "password" as const,
      placeholder: `Enter ${t}`,
    }));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const missing = fields.filter((f) => !values[f.name]?.trim());
    if (missing.length > 0) {
      setError(`Missing: ${missing.map((f) => f.label).join(", ")}`);
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit(values);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="border-t border-[var(--border-subtle)] bg-slate-900/60 backdrop-blur-md px-4 py-4 animate-slide-in">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-2 mb-3">
          <KeyRound size={14} className="text-[var(--color-warning)]" />
          <span className="text-sm font-semibold text-white">
            Credentials Required
          </span>
          {entry?.credential_type && (
            <span className="text-xs text-[var(--text-muted)] bg-white/5 px-2 py-0.5 rounded-full">
              {entry.credential_type}
            </span>
          )}
        </div>
        {entry?.how_to_obtain && (
          <p className="text-xs text-[var(--text-secondary)] mb-3 leading-relaxed">
            {entry.how_to_obtain}
          </p>
        )}
        <form onSubmit={handleSubmit} className="space-y-2">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {fields.map((field) => (
              <div key={field.name} className="flex flex-col gap-1">
                <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wide">
                  {field.label}
                </label>
                <input
                  type={field.type}
                  value={values[field.name] ?? ""}
                  onChange={(e) =>
                    setValues((p) => ({ ...p, [field.name]: e.target.value }))
                  }
                  placeholder={field.placeholder ?? `Enter ${field.label}`}
                  className="bg-[var(--bg-elevated)] border border-[var(--border-muted)] rounded-lg px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-indigo)] transition-colors duration-200"
                />
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between pt-1">
            {error && (
              <p className="text-xs text-[var(--color-error)]">{error}</p>
            )}
            <div className="ml-auto flex gap-2">
              <button
                type="button"
                onClick={() =>
                  setValues(buildInitialValues(guide, pendingTypes))
                }
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-[var(--text-secondary)] hover:text-white hover:bg-white/5 transition-all duration-200"
              >
                <X size={11} /> Clear
              </button>
              <button
                type="submit"
                disabled={submitting}
                className={clsx(
                  "flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200",
                  "bg-[var(--color-warning)] hover:bg-amber-400 text-black shadow-lg",
                  submitting && "opacity-60 cursor-not-allowed",
                )}
              >
                <Send size={12} />
                {submitting ? "Sending…" : "Submit Credentials"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
