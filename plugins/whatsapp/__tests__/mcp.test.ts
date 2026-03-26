import { vi, describe, it, expect } from 'vitest'
import { handleReply, type WhatsAppSock } from '../mcp.js'

describe('handleReply', () => {
  it('returns error when sock is null (not yet connected)', async () => {
    const result = await handleReply({ chat_id: 'jid@s.whatsapp.net', text: 'hi' }, null)
    expect(result.isError).toBe(true)
    expect(result.content[0].text).toBe('WhatsApp socket not connected yet')
  })

  it('sends message and returns success response', async () => {
    const sock: WhatsAppSock = { sendMessage: vi.fn().mockResolvedValue(undefined) }
    const result = await handleReply({ chat_id: '+1234567890@s.whatsapp.net', text: 'hello' }, sock)
    expect(sock.sendMessage).toHaveBeenCalledWith('+1234567890@s.whatsapp.net', { text: 'hello' })
    expect(result.isError).toBeUndefined()
    expect(result.content[0].text).toBe('Message sent')
  })

  it('returns error response when sendMessage throws an Error', async () => {
    const sock: WhatsAppSock = {
      sendMessage: vi.fn().mockRejectedValue(new Error('Connection lost')),
    }
    const result = await handleReply({ chat_id: 'jid', text: 'hi' }, sock)
    expect(result.isError).toBe(true)
    expect(result.content[0].text).toBe('Failed to send message: Connection lost')
  })

  it('returns error response when sendMessage throws a non-Error value', async () => {
    const sock: WhatsAppSock = {
      sendMessage: vi.fn().mockRejectedValue('socket closed'),
    }
    const result = await handleReply({ chat_id: 'jid', text: 'hi' }, sock)
    expect(result.isError).toBe(true)
    expect(result.content[0].text).toBe('Failed to send message: socket closed')
  })
})
