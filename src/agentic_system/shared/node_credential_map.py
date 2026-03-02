"""
Static mapping of n8n node types to their credential type options,
and integration name aliases for non-standard naming conventions.

Extracted from n8n-nodes-base v2.9.2. The Credential Scanner uses
this map — no LLM, no Docker exec, pure deterministic Python.
"""

NODE_CREDENTIAL_MAP: dict[str, list[str]] = {
    # Single option
    "telegram": ["telegramApi"],
    "openAi": ["openAiApi"],
    "discord": ["discordApi"],
    "airtable": ["airtableTokenApi"],
    "notion": ["notionApi"],
    "github": ["githubApi"],
    "jira": ["jiraSoftwareCloudApi"],
    "trello": ["trelloApi"],
    "twilio": ["twilioApi"],
    "sendGrid": ["sendGridApi"],
    "stripe": ["stripeApi"],
    "shopify": ["shopifyApi"],
    "hubspot": ["hubspotApi"],
    "asana": ["asanaApi"],
    "clickUp": ["clickUpApi"],
    "linear": ["linearApi"],
    "supabase": ["supabaseApi"],

    # Multiple options — scanner asks user to pick
    "slack": ["slackApi", "slackOAuth2Api"],
    "googleSheets": ["googleApi", "googleSheetsOAuth2Api"],
    "gmail": ["googleApi", "gmailOAuth2"],
    "googleDrive": ["googleApi", "googleDriveOAuth2Api"],
    "googleCalendar": ["googleApi", "googleCalendarOAuth2Api"],
    "microsoftOutlook": ["microsoftOutlookOAuth2Api"],
    "microsoftTeams": ["microsoftTeamsOAuth2Api"],

    "googleGemini": ["googlePalmApi"],
    "googleBigQuery": ["googleApi", "googleBigQueryOAuth2Api"],
    "googleDocs": ["googleApi", "googleDocsOAuth2Api"],
    "microsoftExcel": ["microsoftExcelOAuth2Api"],
    "dropbox": ["dropboxApi", "dropboxOAuth2Api"],
    "aws": ["aws"],
    "openRouter": ["openRouterApi"],

    # Optional auth — can run unauthenticated
    "webhook": [],
    "httpRequest": ["httpBasicAuth", "httpHeaderAuth"],

    # Code / Function nodes — no credentials
    "code": [],
    "set": [],
    "if": [],
    "switch": [],
    "merge": [],
    "splitInBatches": [],
    "noOp": [],
}


INTEGRATION_ALIASES: dict[str, str] = {
    "gemini": "googleGemini",
    "google gemini": "googleGemini",
    "google sheets": "googleSheets",
    "google drive": "googleDrive",
    "google calendar": "googleCalendar",
    "google docs": "googleDocs",
    "google bigquery": "googleBigQuery",
    "bigquery": "googleBigQuery",
    "outlook": "microsoftOutlook",
    "microsoft outlook": "microsoftOutlook",
    "teams": "microsoftTeams",
    "microsoft teams": "microsoftTeams",
    "excel": "microsoftExcel",
    "microsoft excel": "microsoftExcel",
    "openai": "openAi",
    "open ai": "openAi",
    "sendgrid": "sendGrid",
    "clickup": "clickUp",
    "split in batches": "splitInBatches",
    "http request": "httpRequest",
    "http": "httpRequest",
    "google palm": "googleGemini",
    "google generative ai": "googleGemini",
    "google ai": "googleGemini",
}


def get_credential_types(node_type: str) -> list[str]:
    """Return possible credential types for a node, empty list if none needed."""
    return NODE_CREDENTIAL_MAP.get(node_type, [])
