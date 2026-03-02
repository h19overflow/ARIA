export type NodeColor = 'indigo' | 'blue' | 'cyan' | 'violet' | 'green' | 'amber' | 'orange' | 'gray'

export interface NodeColorDef {
  fill: string
  accent: string
  glow: string
}

export const COLOR_MAP: Record<NodeColor, NodeColorDef> = {
  indigo: { fill: 'rgba(99,102,241,0.12)',  accent: '#6366f1', glow: 'rgba(99,102,241,0.5)' },
  blue:   { fill: 'rgba(59,130,246,0.1)',   accent: '#3b82f6', glow: 'rgba(59,130,246,0.5)' },
  cyan:   { fill: 'rgba(6,182,212,0.1)',    accent: '#06b6d4', glow: 'rgba(6,182,212,0.5)' },
  violet: { fill: 'rgba(139,92,246,0.1)',   accent: '#8b5cf6', glow: 'rgba(139,92,246,0.5)' },
  green:  { fill: 'rgba(16,185,129,0.1)',   accent: '#10b981', glow: 'rgba(16,185,129,0.5)' },
  amber:  { fill: 'rgba(245,158,11,0.1)',   accent: '#f59e0b', glow: 'rgba(245,158,11,0.5)' },
  orange: { fill: 'rgba(249,115,22,0.1)',   accent: '#f97316', glow: 'rgba(249,115,22,0.5)' },
  gray:   { fill: 'rgba(30,34,48,0.9)',     accent: '#6b7280', glow: 'rgba(107,114,128,0.4)' },
}

export const COLOR_ICONS: Record<NodeColor, string> = {
  indigo: '⚡', blue: '✉', cyan: '↗', violet: '⬡', green: '▦', amber: '{ }', orange: '⑂', gray: '◈',
}

export function detectNodeColor(name: string): NodeColor {
  const n = name.toLowerCase()
  if (/webhook|trigger|schedule|cron/.test(n)) return 'indigo'
  if (/gmail|email|mail/.test(n)) return 'blue'
  if (/sheets|notion|airtable|database/.test(n)) return 'green'
  if (/slack|discord|telegram/.test(n)) return 'violet'
  if (/http|api|request|fetch|url/.test(n)) return 'cyan'
  if (/code|function|transform|set|js/.test(n)) return 'amber'
  if (/if|switch|branch|condition|filter/.test(n)) return 'orange'
  return 'gray'
}

export function formatNodeLabel(name: string): string {
  return name.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1').trim().slice(0, 20)
}
