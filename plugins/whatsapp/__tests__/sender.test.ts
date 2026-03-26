import { vi, describe, it, expect, beforeEach } from 'vitest'

vi.mock('fs')

import fs from 'fs'
import { resolveLid, extractSender } from '../sender.js'

describe('resolveLid', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('returns E.164 phone when matching lid-mapping file found', () => {
    vi.mocked(fs.readdirSync).mockReturnValue(['lid-mapping-1234567890.json'] as any)
    vi.mocked(fs.readFileSync).mockReturnValue('"abc123"' as any)
    expect(resolveLid('abc123', '/authDir')).toBe('+1234567890')
  })

  it('returns null when stored lid does not match', () => {
    vi.mocked(fs.readdirSync).mockReturnValue(['lid-mapping-1234567890.json'] as any)
    vi.mocked(fs.readFileSync).mockReturnValue('"different-lid"' as any)
    expect(resolveLid('abc123', '/authDir')).toBeNull()
  })

  it('returns null when authDir is empty', () => {
    vi.mocked(fs.readdirSync).mockReturnValue([] as any)
    expect(resolveLid('abc123', '/authDir')).toBeNull()
  })

  it('returns null when readdirSync throws', () => {
    vi.mocked(fs.readdirSync).mockImplementation(() => { throw new Error('ENOENT') })
    expect(resolveLid('abc123', '/authDir')).toBeNull()
  })

  it('skips files that do not match lid-mapping pattern', () => {
    vi.mocked(fs.readdirSync).mockReturnValue(['auth.json', 'creds.json'] as any)
    expect(resolveLid('abc123', '/authDir')).toBeNull()
    expect(fs.readFileSync).not.toHaveBeenCalled()
  })

  it('returns first matching mapping when multiple files exist', () => {
    vi.mocked(fs.readdirSync).mockReturnValue([
      'lid-mapping-9999999999.json',
      'lid-mapping-1234567890.json',
    ] as any)
    vi.mocked(fs.readFileSync)
      .mockReturnValueOnce('"other-lid"' as any)
      .mockReturnValueOnce('"abc123"' as any)
    expect(resolveLid('abc123', '/authDir')).toBe('+1234567890')
  })
})

describe('extractSender', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('adds + prefix to bare number @s.whatsapp.net JID', () => {
    expect(extractSender('1234567890@s.whatsapp.net', '/authDir')).toBe('+1234567890')
  })

  it('keeps existing + prefix in @s.whatsapp.net JID', () => {
    expect(extractSender('+1234567890@s.whatsapp.net', '/authDir')).toBe('+1234567890')
  })

  it('resolves @lid JID to E.164 when mapping exists', () => {
    vi.mocked(fs.readdirSync).mockReturnValue(['lid-mapping-1234567890.json'] as any)
    vi.mocked(fs.readFileSync).mockReturnValue('"abc123"' as any)
    expect(extractSender('abc123@lid', '/authDir')).toBe('+1234567890')
  })

  it('returns lid: prefix when @lid JID cannot be resolved', () => {
    vi.mocked(fs.readdirSync).mockReturnValue([] as any)
    expect(extractSender('unknownlid@lid', '/authDir')).toBe('lid:unknownlid')
  })

  it('returns raw JID for unknown suffix (e.g. group)', () => {
    expect(extractSender('12345@g.us', '/authDir')).toBe('12345@g.us')
  })
})
