import { vi, describe, it, expect, beforeEach } from 'vitest'

vi.mock('fs')

import fs from 'fs'
import path from 'path'
import {
  inboxWrite,
  inboxDelete,
  inboxReadAll,
  sendNotification,
  drainInbox,
  type InboxEntry,
  type McpServer,
} from '../inbox.js'

const mockEntry: InboxEntry = {
  content: 'hello',
  meta: { chat_id: '+1234567890@s.whatsapp.net', sender: '+1234567890' },
}

describe('inboxWrite', () => {
  beforeEach(() => vi.resetAllMocks())

  it('writes JSON entry to inboxDir and returns the file path', () => {
    vi.mocked(fs.writeFileSync).mockReturnValue(undefined)
    const file = inboxWrite(mockEntry, '/inbox')
    expect(file).toMatch(/^\/inbox\/\d+-\w+\.json$/)
    expect(fs.writeFileSync).toHaveBeenCalledWith(file, JSON.stringify(mockEntry))
  })
})

describe('inboxDelete', () => {
  beforeEach(() => vi.resetAllMocks())

  it('deletes the specified file', () => {
    vi.mocked(fs.unlinkSync).mockReturnValue(undefined)
    inboxDelete('/inbox/msg.json')
    expect(fs.unlinkSync).toHaveBeenCalledWith('/inbox/msg.json')
  })

  it('does not throw when file does not exist', () => {
    vi.mocked(fs.unlinkSync).mockImplementation(() => { throw new Error('ENOENT') })
    expect(() => inboxDelete('/inbox/missing.json')).not.toThrow()
  })
})

describe('inboxReadAll', () => {
  beforeEach(() => vi.resetAllMocks())

  it('returns empty array when inboxDir does not exist', () => {
    vi.mocked(fs.readdirSync).mockImplementation(() => { throw new Error('ENOENT') })
    expect(inboxReadAll('/inbox')).toEqual([])
  })

  it('returns empty array for an empty directory', () => {
    vi.mocked(fs.readdirSync).mockReturnValue([] as any)
    expect(inboxReadAll('/inbox')).toEqual([])
  })

  it('returns entries sorted by filename', () => {
    vi.mocked(fs.readdirSync).mockReturnValue(['2-bbb.json', '1-aaa.json'] as any)
    vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify(mockEntry) as any)

    const result = inboxReadAll('/inbox')

    expect(result).toHaveLength(2)
    expect(result[0].file).toBe(path.join('/inbox', '1-aaa.json'))
    expect(result[1].file).toBe(path.join('/inbox', '2-bbb.json'))
    expect(result[0].entry).toEqual(mockEntry)
  })

  it('skips non-.json files', () => {
    vi.mocked(fs.readdirSync).mockReturnValue(['msg.json', 'README.txt'] as any)
    vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify(mockEntry) as any)
    expect(inboxReadAll('/inbox')).toHaveLength(1)
  })

  it('skips and deletes corrupt JSON files', () => {
    vi.mocked(fs.readdirSync).mockReturnValue(['corrupt.json'] as any)
    vi.mocked(fs.readFileSync).mockReturnValue('not-valid-json' as any)
    vi.mocked(fs.unlinkSync).mockReturnValue(undefined)

    const result = inboxReadAll('/inbox')

    expect(result).toHaveLength(0)
    expect(fs.unlinkSync).toHaveBeenCalledWith(path.join('/inbox', 'corrupt.json'))
  })
})

describe('sendNotification', () => {
  beforeEach(() => vi.resetAllMocks())

  it('sends notification and returns true on success', async () => {
    const mcp: McpServer = { notification: vi.fn().mockResolvedValue(undefined) }
    const result = await sendNotification(mcp, mockEntry)
    expect(mcp.notification).toHaveBeenCalledWith({
      method: 'notifications/claude/channel',
      params: { content: mockEntry.content, meta: mockEntry.meta },
    })
    expect(result).toBe(true)
  })

  it('deletes inbox file on success when inboxFile provided', async () => {
    vi.mocked(fs.unlinkSync).mockReturnValue(undefined)
    const mcp: McpServer = { notification: vi.fn().mockResolvedValue(undefined) }
    await sendNotification(mcp, mockEntry, '/inbox/msg.json')
    expect(fs.unlinkSync).toHaveBeenCalledWith('/inbox/msg.json')
  })

  it('returns false and does not delete file when notification throws', async () => {
    const mcp: McpServer = { notification: vi.fn().mockRejectedValue(new Error('MCP not ready')) }
    const result = await sendNotification(mcp, mockEntry, '/inbox/msg.json')
    expect(result).toBe(false)
    expect(fs.unlinkSync).not.toHaveBeenCalled()
  })
})

describe('drainInbox', () => {
  beforeEach(() => vi.resetAllMocks())

  it('replays all pending entries', async () => {
    vi.mocked(fs.readdirSync).mockReturnValue(['1-aaa.json', '2-bbb.json'] as any)
    vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify(mockEntry) as any)
    vi.mocked(fs.unlinkSync).mockReturnValue(undefined)
    const mcp: McpServer = { notification: vi.fn().mockResolvedValue(undefined) }

    await drainInbox('/inbox', mcp)

    expect(mcp.notification).toHaveBeenCalledTimes(2)
  })

  it('leaves failed entries in inbox (does not delete)', async () => {
    vi.mocked(fs.readdirSync).mockReturnValue(['1-aaa.json'] as any)
    vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify(mockEntry) as any)
    const mcp: McpServer = { notification: vi.fn().mockRejectedValue(new Error('fail')) }

    await drainInbox('/inbox', mcp)

    expect(fs.unlinkSync).not.toHaveBeenCalled()
  })

  it('resolves immediately with no-op when inbox is empty', async () => {
    vi.mocked(fs.readdirSync).mockReturnValue([] as any)
    const mcp: McpServer = { notification: vi.fn() }
    await expect(drainInbox('/inbox', mcp)).resolves.toBeUndefined()
    expect(mcp.notification).not.toHaveBeenCalled()
  })
})
