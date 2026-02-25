import type { GuideStep } from './PageGuide'

export const CONVERSATION_GUIDE: GuideStep[] = [
  {
    label: 'Describe what you want to automate',
    detail: 'Tell ARIA in plain English. E.g. "When I get a Gmail, save the attachment to Google Drive and notify me on Slack."',
  },
  {
    label: 'Review the extracted requirements',
    detail: 'The left panel fills in as you chat. Edit any field if ARIA got something wrong.',
  },
  {
    label: 'Run Preflight when ready',
    detail: 'Once requirements are captured and committed, hit "Run Preflight" to move to analysis.',
  },
]

export const PREFLIGHT_GUIDE: GuideStep[] = [
  {
    label: 'ARIA analyses your requirements',
    detail: 'The orchestrator parses your intent and identifies which n8n nodes are needed.',
  },
  {
    label: 'Connect any missing credentials',
    detail: 'If a service needs authentication, you\'ll be prompted to provide API keys or OAuth tokens.',
  },
  {
    label: 'Review the blueprint and start building',
    detail: 'Once all nodes and credentials are resolved, click "Start Building" to begin Phase 2.',
  },
]

export const BUILD_GUIDE: GuideStep[] = [
  {
    label: 'ARIA assembles the n8n workflow',
    detail: 'Nodes are created, connected, and configured automatically. Watch the graph appear in real time.',
  },
  {
    label: 'The workflow is tested automatically',
    detail: 'ARIA executes the workflow and checks for errors. If something fails, it will attempt to fix it.',
  },
  {
    label: 'Your workflow goes live',
    detail: 'Once tests pass, the workflow is activated in n8n. You\'ll get a webhook URL if applicable.',
  },
]
