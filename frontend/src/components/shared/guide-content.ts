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
    label: 'Start Build when ready',
    detail: 'Once requirements and credentials are resolved, hit "Start Build" to begin building your workflow.',
  },
]

export const BUILD_GUIDE: GuideStep[] = [
  {
    label: 'ARIA assembles the n8n workflow',
    detail: 'Nodes are created, connected, and configured automatically. Watch the graph appear in real time.',
  },
  {
    label: 'Your workflow is deployed to n8n',
    detail: 'Once built, the workflow is saved as an inactive draft. Open it in n8n to review and activate.',
  },
]
