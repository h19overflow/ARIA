export interface CredentialField {
  name: string
  label: string
  description: string
  required: boolean
  type?: 'text' | 'password' | 'url'
  placeholder?: string
  options?: string[]
}

export interface CredentialGuideEntry {
  credential_type: string
  display_name: string
  service_description: string
  how_to_obtain: string
  help_url: string
  fields: CredentialField[]
}

export interface CredentialGuidePayload {
  entries: CredentialGuideEntry[]
  summary: string
}
