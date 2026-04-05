import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js'

export interface WhatsAppSock {
  sendMessage(jid: string, content: { text: string }): Promise<unknown>
}

export async function handleReply(
  args: { chat_id: string; text: string },
  sock: WhatsAppSock | null,
  isConnected: boolean,
): Promise<{ content: Array<{ type: string; text: string }>; isError?: boolean }> {
  if (!isConnected || !sock) {
    return { content: [{ type: 'text', text: 'WhatsApp not connected — reconnecting, please retry shortly' }], isError: true }
  }
  try {
    await sock.sendMessage(args.chat_id, { text: args.text })
    return { content: [{ type: 'text', text: 'Message sent' }] }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { content: [{ type: 'text', text: `Failed to send message: ${message}` }], isError: true }
  }
}

export function createMcpServer(getSock: () => WhatsAppSock | null, getConnected: () => boolean): Server {
  const mcp = new Server(
    { name: 'whatsapp', version: '0.0.1' },
    {
      capabilities: {
        experimental: { 'claude/channel': {} },
        tools: {},
      },
      instructions: `WhatsApp messages arrive as <channel source="whatsapp" chat_id="..." sender="...">message text</channel>.
The chat_id is the WhatsApp JID (e.g. +1234567890@s.whatsapp.net). Reply using the reply tool with that chat_id.
The sender field is the E.164 phone number. Only messages from allowed senders reach you.`,
    },
  )

  mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: [
      {
        name: 'reply',
        description: 'Send a WhatsApp message back to a chat',
        inputSchema: {
          type: 'object',
          properties: {
            chat_id: {
              type: 'string',
              description: 'WhatsApp JID (e.g. +1234567890@s.whatsapp.net)',
            },
            text: {
              type: 'string',
              description: 'Message text to send',
            },
          },
          required: ['chat_id', 'text'],
        },
      },
    ],
  }))

  mcp.setRequestHandler(CallToolRequestSchema, async (req) => {
    const { name, arguments: args } = req.params
    if (name !== 'reply') {
      return { content: [{ type: 'text', text: `Unknown tool: ${name}` }], isError: true }
    }
    return handleReply(args as { chat_id: string; text: string }, getSock(), getConnected())
  })

  return mcp
}
