import type { ConversationNotes } from './types';

const GRANULAR_FIELDS = new Set([
  'trigger_type', 'trigger_service', 'trigger_schedule', 'trigger_event',
  'transform', 'destination_service', 'destination_action', 'destination_format',
]);

const KNOWN_FIELDS = new Set([
  'summary', 'trigger', 'destination', 'data_transform', ...GRANULAR_FIELDS,
]);

export function deriveTrigger(notes: ConversationNotes): string {
  const parts = [notes.trigger_type, notes.trigger_service, notes.trigger_schedule, notes.trigger_event].filter(Boolean);
  return parts.join(' — ') || notes.trigger || '';
}

export function deriveDestination(notes: ConversationNotes): string {
  const parts = [notes.destination_service, notes.destination_action, notes.destination_format].filter(Boolean);
  return parts.join(' — ') || notes.destination || '';
}

export function applyNoteTaken(prev: ConversationNotes, key: string, value: unknown): ConversationNotes {
  const next = { ...prev };
  if (value === null) {
    if (key in next) {
      delete (next as Record<string, unknown>)[key];
    } else if (next.raw_notes && key in next.raw_notes) {
      next.raw_notes = { ...next.raw_notes };
      delete next.raw_notes[key];
    }
  } else if (key === 'constraints' || key === 'required_integrations') {
    const current = (next as Record<string, unknown>)[key];
    const arr = Array.isArray(current) ? current : [];
    if (Array.isArray(value)) {
      (next as Record<string, unknown>)[key] = value;
    } else if (typeof value === 'string' && !arr.includes(value)) {
      (next as Record<string, unknown>)[key] = [...arr, value];
    }
  } else if (KNOWN_FIELDS.has(key)) {
    (next as Record<string, unknown>)[key] = value;
  } else {
    next.raw_notes = { ...(next.raw_notes ?? {}), [key]: String(value) };
  }

  if (key.startsWith('trigger_')) {
    next.trigger = deriveTrigger(next);
  } else if (key.startsWith('destination_')) {
    next.destination = deriveDestination(next);
  } else if (key === 'transform') {
    next.data_transform = String(value ?? '');
  }
  return next;
}
