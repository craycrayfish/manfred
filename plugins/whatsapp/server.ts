import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { makeWASocket, DisconnectReason, useMultiFileAuthState, fetchLatestWaWebVersion } from '@whiskeysockets/baileys'
import { Boom } from '@hapi/boom'
import P from 'pino'
import fs from 'fs'
import os from 'os'
import path from 'path'
import { isAllowed } from './access.js'
import { extractSender } from './sender.js'
import { inboxWrite, drainInbox, startDrainLoop } from './inbox.js'
import { createMcpServer } from './mcp.js'

// State directory layout
const stateDir = path.join(os.homedir(), '.claude', 'channels', 'whatsapp')
const authDir = path.join(stateDir, 'auth')
const accessFile = path.join(stateDir, 'access.json')
const inboxDir = path.join(stateDir, 'inbox')

// Ensure directories exist
fs.mkdirSync(authDir, { recursive: true })
fs.mkdirSync(inboxDir, { recursive: true })

// WhatsApp socket and connection state
let sock: ReturnType<typeof makeWASocket> | null = null
let isConnected = false

// MCP server
const mcp = createMcpServer(() => sock, () => isConnected)

// Baileys connection
async function connectWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(authDir)
  const { version } = await fetchLatestWaWebVersion()

  sock = makeWASocket({ auth: state, version, logger: P({ level: 'silent' }) })

  sock.ev.on('creds.update', saveCreds)

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update
    if (qr) {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      import('qrcode-terminal').then(({ default: qrcode }) => {
        qrcode.generate(qr, { small: true }, (qrString: string) => {
          process.stderr.write(`[whatsapp] Scan QR code to connect:\n${qrString}\n`)
        })
      })
    }

    if (connection === 'open') {
      isConnected = true
      process.stderr.write('[whatsapp] Connected\n')
    }

    if (connection === 'close') {
      isConnected = false
      sock = null
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
      const sender = extractSender(jid, authDir)
      const text =
        msg.message.conversation ||
        msg.message.extendedTextMessage?.text ||
        ''

      if (!text) continue
      if (!isAllowed(sender, accessFile)) continue

      const entry = { content: text, meta: { chat_id: jid, sender } }
      inboxWrite(entry, inboxDir)
    }
  })
}

// Start: await WhatsApp connection before MCP so listeners are registered first
await connectWhatsApp()
await mcp.connect(new StdioServerTransport())
await drainInbox(inboxDir, mcp)
startDrainLoop(inboxDir, mcp)
