export interface CredentialField {
  name: string
  label: string
  type: 'text' | 'password' | 'url'
  placeholder?: string
}

export interface CredentialGuidePayload {
  credential_type: string
  fields: CredentialField[]
  instructions?: string
}
