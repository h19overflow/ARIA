const DISPLAY_NAMES: Record<string, string> = {
  telegramApi: 'Telegram Bot',
  gmailOAuth2: 'Gmail',
  googleSheetsOAuth2Api: 'Google Sheets',
  googleCalendarOAuth2Api: 'Google Calendar',
  googleDriveOAuth2Api: 'Google Drive',
  slackApi: 'Slack Bot',
  slackOAuth2Api: 'Slack',
  openAiApi: 'OpenAI',
  notionApi: 'Notion',
  githubApi: 'GitHub',
  githubOAuth2Api: 'GitHub',
  discordApi: 'Discord Bot',
  discordOAuth2Api: 'Discord',
  trelloApi: 'Trello',
  airtableApi: 'Airtable',
  shopifyApi: 'Shopify',
  stripeApi: 'Stripe',
  twilioApi: 'Twilio',
  sendGridApi: 'SendGrid',
  hubSpotApi: 'HubSpot',
  hubSpotOAuth2Api: 'HubSpot',
  jiraApi: 'Jira',
  zendeskApi: 'Zendesk',
  asanaApi: 'Asana',
};

const SUFFIXES_TO_STRIP = ['OAuth2Api', 'OAuth2', 'Api'] as const;

export function formatCredentialDisplayName(type: string): string {
  if (DISPLAY_NAMES[type]) return DISPLAY_NAMES[type];

  let base = type;
  for (const suffix of SUFFIXES_TO_STRIP) {
    if (base.endsWith(suffix)) {
      base = base.slice(0, -suffix.length);
      break;
    }
  }

  return base.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/^./, (c) => c.toUpperCase());
}
