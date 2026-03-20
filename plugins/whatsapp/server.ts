import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js'
import makeWASocket, { DisconnectReason, useMultiFileAuthState } from '@whiskeysockets/baileys'
import { Boom } from '@hapi/boom'
import P from 'pino'
import fs from 'fs'
import os from 'os'
import path from 'path'

// State directory layout
const stateDir = path.join(os.homedir(), '.claude', 'channels', 'whatsapp')
const authDir = path.join(stateDir, 'auth')
const accessFile = path.join(stateDir, 'access.json')
const inboxDir = path.join(stateDir, 'inbox')

// Ensure directories exist
fs.mkdirSync(authDir, { recursive: true })
fs.mkdirSync(inboxDir, { recursive: true })

// Access config

interface AccessConfig {
  dmPolicy: 'allowlist' | 'open' | 'disabled'
  allowFrom: string[]
}

const defaultAccessConfig: AccessConfig = { dmPolicy: 'allowlist', allowFrom: [] }

function loadAccessConfig(): AccessConfig {
  try {
    const raw = fs.readFileSync(accessFile, 'utf-8')
    return JSON.parse(raw) as AccessConfig
  } catch {
    return defaultAccessConfig
  }
}

function isAllowed(phone: string): boolean {
  const config = loadAccessConfig()
  if (config.dmPolicy === 'disabled') return false
  if (config.dmPolicy === 'open') return true
  return config.allowFrom.includes(phone)
}

// MCP server

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

// WhatsApp socket (assigned after connect)
let sock: ReturnType<typeof makeWASocket> | null = null

mcp.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params
  if (name !== 'reply') {
    return { content: [{ type: 'text', text: `Unknown tool: ${name}` }], isError: true }
  }

  const { chat_id, text } = args as { chat_id: string; text: string }

  if (!sock) {
    return { content: [{ type: 'text', text: 'WhatsApp socket not connected yet' }], isError: true }
  }

  try {
    await sock.sendMessage(chat_id, { text })
    return { content: [{ type: 'text', text: 'Message sent' }] }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { content: [{ type: 'text', text: `Failed to send message: ${message}` }], isError: true }
  }
})

// Baileys connection

async function connectWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(authDir)

  sock = makeWASocket({ auth: state, printQRInTerminal: false, logger: P({ level: 'silent' }) })

  sock.ev.on('creds.update', saveCreds)

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update
    if (qr) {
      process.stderr.write(`[whatsapp] Scan QR code to connect:\n${qr}\n`)
    }

    if (connection === 'close') {
      const reason = (lastDisconnect?.error as Boom)?.output?.statusCode
      if (reason === DisconnectReason.loggedOut) {
        process.stderr.write('[whatsapp] Logged out — run /whatsapp:configure qr to re-authenticate\n')
      } else {
        process.stderr.write('[whatsapp] Connection closed, reconnecting...\n')
        connectWhatsApp()
      }
    }
  })

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return
    for (const msg of messages) {
      if (msg.key.fromMe) continue
      if (!msg.message) continue

      const jid = msg.key.remoteJid!
      const sender = jid.replace('@s.whatsapp.net', '')
      const text =
        msg.message.conversation ||
        msg.message.extendedTextMessage?.text ||
        ''

      if (!text) continue
      if (!isAllowed(sender)) continue

      try {
        await mcp.notification({
          method: 'notifications/claude/channel',
          params: {
            content: text,
            meta: { chat_id: jid, sender },
          },
        })
      } catch (err) {
        process.stderr.write(`[whatsapp] Failed to send notification: ${err}\n`)
      }
    }
  })
}

// Start

connectWhatsApp()
await mcp.connect(new StdioServerTransport())
