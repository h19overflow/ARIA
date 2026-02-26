"""Static credential guide data for known n8n credential types.

This is a pure data file -- no logic. It exceeds the 150-line limit by design
because it maps ~28 credential types to human-readable guide prose. Each entry
provides display_name, service_description, how_to_obtain steps, and a real
developer portal URL.

All URLs have been verified against official documentation portals.
"""
from __future__ import annotations

CREDENTIAL_GUIDES: dict[str, dict[str, str]] = {
    "telegramApi": {
        "display_name": "Telegram Bot API",
        "service_description": "Telegram is a messaging platform with a Bot API for automated interactions.",
        "how_to_obtain": (
            "1. Open Telegram and message @BotFather.\n"
            "2. Send /newbot and follow the prompts to name your bot.\n"
            "3. Copy the HTTP API token BotFather gives you."
        ),
        "help_url": "https://core.telegram.org/bots#botfather",
    },
    "openAiApi": {
        "display_name": "OpenAI API",
        "service_description": "OpenAI provides large language models for text generation, embeddings, and more.",
        "how_to_obtain": (
            "1. Sign in at platform.openai.com.\n"
            "2. Go to API Keys in your account settings.\n"
            "3. Click 'Create new secret key' and copy it."
        ),
        "help_url": "https://platform.openai.com/api-keys",
    },
    "discordApi": {
        "display_name": "Discord Bot",
        "service_description": "Discord is a communication platform with a Bot API for server automation.",
        "how_to_obtain": (
            "1. Go to the Discord Developer Portal.\n"
            "2. Create a new application, then add a Bot.\n"
            "3. Copy the bot token from the Bot settings page."
        ),
        "help_url": "https://discord.com/developers/applications",
    },
    "airtableTokenApi": {
        "display_name": "Airtable Personal Access Token",
        "service_description": "Airtable is a spreadsheet-database hybrid for collaborative data management.",
        "how_to_obtain": (
            "1. Go to airtable.com/create/tokens.\n"
            "2. Click 'Create new token'.\n"
            "3. Set scopes and base access, then copy the token."
        ),
        "help_url": "https://airtable.com/create/tokens",
    },
    "notionApi": {
        "display_name": "Notion API",
        "service_description": "Notion is an all-in-one workspace for notes, databases, and project management.",
        "how_to_obtain": (
            "1. Go to notion.so/my-integrations.\n"
            "2. Click 'New integration' and configure it.\n"
            "3. Copy the Internal Integration Secret."
        ),
        "help_url": "https://www.notion.so/my-integrations",
    },
    "githubApi": {
        "display_name": "GitHub Personal Access Token",
        "service_description": "GitHub is a platform for version control and collaborative software development.",
        "how_to_obtain": (
            "1. Go to GitHub Settings > Developer settings > Personal access tokens.\n"
            "2. Click 'Generate new token (classic)' or use fine-grained tokens.\n"
            "3. Select scopes, generate, and copy the token."
        ),
        "help_url": "https://github.com/settings/tokens",
    },
    "jiraSoftwareCloudApi": {
        "display_name": "Jira Software Cloud API",
        "service_description": "Jira is an issue-tracking and project management tool by Atlassian.",
        "how_to_obtain": (
            "1. Go to id.atlassian.com/manage-profile/security/api-tokens.\n"
            "2. Click 'Create API token' and give it a label.\n"
            "3. Copy the token and use it with your Atlassian email."
        ),
        "help_url": "https://id.atlassian.com/manage-profile/security/api-tokens",
    },
    "trelloApi": {
        "display_name": "Trello API",
        "service_description": "Trello is a visual project management tool using boards, lists, and cards.",
        "how_to_obtain": (
            "1. Go to trello.com/power-ups/admin.\n"
            "2. Create a new Power-Up to get an API key.\n"
            "3. Generate a token by authorizing your app."
        ),
        "help_url": "https://trello.com/power-ups/admin",
    },
    "twilioApi": {
        "display_name": "Twilio API",
        "service_description": "Twilio provides cloud communication APIs for SMS, voice, and messaging.",
        "how_to_obtain": (
            "1. Sign in at console.twilio.com.\n"
            "2. Find your Account SID and Auth Token on the dashboard.\n"
            "3. Copy both values for use in n8n."
        ),
        "help_url": "https://console.twilio.com/",
    },
    "sendGridApi": {
        "display_name": "SendGrid API",
        "service_description": "SendGrid is a cloud-based email delivery service for transactional and marketing email.",
        "how_to_obtain": (
            "1. Sign in at app.sendgrid.com.\n"
            "2. Go to Settings > API Keys.\n"
            "3. Click 'Create API Key', set permissions, and copy it."
        ),
        "help_url": "https://app.sendgrid.com/settings/api_keys",
    },
    "stripeApi": {
        "display_name": "Stripe API",
        "service_description": "Stripe is a payment processing platform for online businesses.",
        "how_to_obtain": (
            "1. Sign in at dashboard.stripe.com.\n"
            "2. Go to Developers > API keys.\n"
            "3. Copy your Secret key (use test mode key for development)."
        ),
        "help_url": "https://dashboard.stripe.com/apikeys",
    },
    "shopifyApi": {
        "display_name": "Shopify Admin API",
        "service_description": "Shopify is an e-commerce platform for building and managing online stores.",
        "how_to_obtain": (
            "1. In your Shopify admin, go to Settings > Apps and sales channels.\n"
            "2. Click 'Develop apps' and create a new app.\n"
            "3. Configure API scopes, install the app, and copy the Admin API access token."
        ),
        "help_url": "https://shopify.dev/docs/apps/getting-started",
    },
    "hubspotApi": {
        "display_name": "HubSpot API",
        "service_description": "HubSpot is a CRM platform for marketing, sales, and customer service.",
        "how_to_obtain": (
            "1. Go to app.hubspot.com and navigate to Settings > Integrations > Private Apps.\n"
            "2. Create a private app and configure scopes.\n"
            "3. Copy the access token from the Auth tab."
        ),
        "help_url": "https://developers.hubspot.com/docs/api/private-apps",
    },
    "asanaApi": {
        "display_name": "Asana Personal Access Token",
        "service_description": "Asana is a work management platform for organizing tasks and projects.",
        "how_to_obtain": (
            "1. Go to app.asana.com/-/developer_console.\n"
            "2. Click 'Create new token' under Personal Access Tokens.\n"
            "3. Name it and copy the token."
        ),
        "help_url": "https://app.asana.com/-/developer_console",
    },
    "clickUpApi": {
        "display_name": "ClickUp API",
        "service_description": "ClickUp is a productivity platform for project management and team collaboration.",
        "how_to_obtain": (
            "1. In ClickUp, go to Settings > Apps.\n"
            "2. Click 'Generate' under API Token.\n"
            "3. Copy the personal API token."
        ),
        "help_url": "https://clickup.com/api/",
    },
    "linearApi": {
        "display_name": "Linear API",
        "service_description": "Linear is a project management tool for software teams with issue tracking.",
        "how_to_obtain": (
            "1. Go to linear.app, then Settings > API.\n"
            "2. Click 'Create key' under Personal API keys.\n"
            "3. Copy the generated API key."
        ),
        "help_url": "https://linear.app/settings/api",
    },
    "supabaseApi": {
        "display_name": "Supabase API",
        "service_description": "Supabase is an open-source Firebase alternative with a PostgreSQL database.",
        "how_to_obtain": (
            "1. Go to app.supabase.com and open your project.\n"
            "2. Navigate to Settings > API.\n"
            "3. Copy the Project URL and the anon/service_role key."
        ),
        "help_url": "https://app.supabase.com/",
    },
    "slackApi": {
        "display_name": "Slack API (Bot Token)",
        "service_description": "Slack is a business messaging platform for team communication and workflows.",
        "how_to_obtain": (
            "1. Go to api.slack.com/apps and create a new app.\n"
            "2. Under OAuth & Permissions, add required bot scopes.\n"
            "3. Install the app to your workspace and copy the Bot User OAuth Token."
        ),
        "help_url": "https://api.slack.com/apps",
    },
    "slackOAuth2Api": {
        "display_name": "Slack OAuth2",
        "service_description": "Slack is a business messaging platform for team communication and workflows.",
        "how_to_obtain": (
            "1. Go to api.slack.com/apps and create a new app.\n"
            "2. Under OAuth & Permissions, add scopes and set the redirect URL.\n"
            "3. Copy the Client ID and Client Secret from Basic Information."
        ),
        "help_url": "https://api.slack.com/apps",
    },
    "googleApi": {
        "display_name": "Google API Key / Service Account",
        "service_description": "Google Cloud provides APIs for Sheets, Drive, Gmail, Calendar, and more.",
        "how_to_obtain": (
            "1. Go to console.cloud.google.com/apis/credentials.\n"
            "2. Create a project (or select existing), then click 'Create Credentials'.\n"
            "3. Choose API Key or Service Account and copy the credentials."
        ),
        "help_url": "https://console.cloud.google.com/apis/credentials",
    },
    "googleSheetsOAuth2Api": {
        "display_name": "Google Sheets OAuth2",
        "service_description": "Google Sheets is a cloud spreadsheet application in Google Workspace.",
        "how_to_obtain": (
            "1. Go to console.cloud.google.com/apis/credentials.\n"
            "2. Create an OAuth 2.0 Client ID (Web application type).\n"
            "3. Enable the Google Sheets API, then copy Client ID and Client Secret."
        ),
        "help_url": "https://console.cloud.google.com/apis/credentials",
    },
    "gmailOAuth2": {
        "display_name": "Gmail OAuth2",
        "service_description": "Gmail is Google's email service, accessible via API for sending and reading mail.",
        "how_to_obtain": (
            "1. Go to console.cloud.google.com/apis/credentials.\n"
            "2. Create an OAuth 2.0 Client ID (Web application type).\n"
            "3. Enable the Gmail API, then copy Client ID and Client Secret."
        ),
        "help_url": "https://console.cloud.google.com/apis/credentials",
    },
    "googleDriveOAuth2Api": {
        "display_name": "Google Drive OAuth2",
        "service_description": "Google Drive is a cloud storage and file-sharing service.",
        "how_to_obtain": (
            "1. Go to console.cloud.google.com/apis/credentials.\n"
            "2. Create an OAuth 2.0 Client ID (Web application type).\n"
            "3. Enable the Google Drive API, then copy Client ID and Client Secret."
        ),
        "help_url": "https://console.cloud.google.com/apis/credentials",
    },
    "googleCalendarOAuth2Api": {
        "display_name": "Google Calendar OAuth2",
        "service_description": "Google Calendar is a scheduling and time-management service.",
        "how_to_obtain": (
            "1. Go to console.cloud.google.com/apis/credentials.\n"
            "2. Create an OAuth 2.0 Client ID (Web application type).\n"
            "3. Enable the Google Calendar API, then copy Client ID and Client Secret."
        ),
        "help_url": "https://console.cloud.google.com/apis/credentials",
    },
    "microsoftOutlookOAuth2Api": {
        "display_name": "Microsoft Outlook OAuth2",
        "service_description": "Microsoft Outlook provides email, calendar, and contacts via Microsoft 365.",
        "how_to_obtain": (
            "1. Go to portal.azure.com > Azure Active Directory > App registrations.\n"
            "2. Register a new application and add Mail/Calendar API permissions.\n"
            "3. Create a client secret and copy the Application (client) ID and secret."
        ),
        "help_url": "https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade",
    },
    "microsoftTeamsOAuth2Api": {
        "display_name": "Microsoft Teams OAuth2",
        "service_description": "Microsoft Teams is a collaboration platform for chat, meetings, and file sharing.",
        "how_to_obtain": (
            "1. Go to portal.azure.com > Azure Active Directory > App registrations.\n"
            "2. Register a new application and add Teams API permissions.\n"
            "3. Create a client secret and copy the Application (client) ID and secret."
        ),
        "help_url": "https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade",
    },
    "httpBasicAuth": {
        "display_name": "HTTP Basic Auth",
        "service_description": "HTTP Basic Authentication sends a username and password with each request.",
        "how_to_obtain": (
            "1. Obtain a username and password from the target service.\n"
            "2. Enter them in the credential fields below."
        ),
        "help_url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication",
    },
    "httpHeaderAuth": {
        "display_name": "HTTP Header Auth",
        "service_description": "HTTP Header Authentication sends a custom header (e.g., API key) with each request.",
        "how_to_obtain": (
            "1. Obtain your API key or token from the target service.\n"
            "2. Enter the header name and value in the credential fields below."
        ),
        "help_url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Authorization",
    },
}
