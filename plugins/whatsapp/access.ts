import fs from 'fs'

export interface AccessConfig {
  dmPolicy: 'allowlist' | 'open' | 'disabled'
  allowFrom: string[]
}

export const defaultAccessConfig: AccessConfig = { dmPolicy: 'allowlist', allowFrom: [] }

export function loadAccessConfig(accessFile: string): AccessConfig {
  try {
    const raw = fs.readFileSync(accessFile, 'utf-8')
    return JSON.parse(raw) as AccessConfig
  } catch {
    return { ...defaultAccessConfig }
  }
}

export function isAllowed(phone: string, accessFile: string): boolean {
  const config = loadAccessConfig(accessFile)
  if (config.dmPolicy === 'disabled') return false
  if (config.dmPolicy === 'open') return true
  return config.allowFrom.includes(phone)
}
