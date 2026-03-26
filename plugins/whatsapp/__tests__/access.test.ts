import { vi, describe, it, expect, beforeEach } from 'vitest'

vi.mock('fs')

import fs from 'fs'
import { loadAccessConfig, isAllowed, defaultAccessConfig } from '../access.js'

describe('loadAccessConfig', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('returns default config when file does not exist', () => {
    vi.mocked(fs.readFileSync).mockImplementation(() => { throw new Error('ENOENT') })
    expect(loadAccessConfig('/some/access.json')).toEqual(defaultAccessConfig)
  })

  it('returns parsed config from valid JSON file', () => {
    const config = { dmPolicy: 'open' as const, allowFrom: ['+1234567890'] }
    vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify(config) as any)
    expect(loadAccessConfig('/some/access.json')).toEqual(config)
  })

  it('returns default config when file contains malformed JSON', () => {
    vi.mocked(fs.readFileSync).mockReturnValue('not-json' as any)
    expect(loadAccessConfig('/some/access.json')).toEqual(defaultAccessConfig)
  })
})

describe('isAllowed', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('returns false when dmPolicy is disabled', () => {
    vi.mocked(fs.readFileSync).mockReturnValue(
      JSON.stringify({ dmPolicy: 'disabled', allowFrom: ['+1234567890'] }) as any,
    )
    expect(isAllowed('+1234567890', '/access.json')).toBe(false)
  })

  it('returns true for any phone when dmPolicy is open', () => {
    vi.mocked(fs.readFileSync).mockReturnValue(
      JSON.stringify({ dmPolicy: 'open', allowFrom: [] }) as any,
    )
    expect(isAllowed('+9999999999', '/access.json')).toBe(true)
  })

  it('returns true for phone in allowlist', () => {
    vi.mocked(fs.readFileSync).mockReturnValue(
      JSON.stringify({ dmPolicy: 'allowlist', allowFrom: ['+1234567890'] }) as any,
    )
    expect(isAllowed('+1234567890', '/access.json')).toBe(true)
  })

  it('returns false for phone not in allowlist', () => {
    vi.mocked(fs.readFileSync).mockReturnValue(
      JSON.stringify({ dmPolicy: 'allowlist', allowFrom: ['+1234567890'] }) as any,
    )
    expect(isAllowed('+9999999999', '/access.json')).toBe(false)
  })

  it('returns false for empty allowlist', () => {
    vi.mocked(fs.readFileSync).mockReturnValue(
      JSON.stringify({ dmPolicy: 'allowlist', allowFrom: [] }) as any,
    )
    expect(isAllowed('+1234567890', '/access.json')).toBe(false)
  })

  it('returns false when config file is missing (falls back to default allowlist policy)', () => {
    vi.mocked(fs.readFileSync).mockImplementation(() => { throw new Error('ENOENT') })
    expect(isAllowed('+1234567890', '/access.json')).toBe(false)
  })
})
