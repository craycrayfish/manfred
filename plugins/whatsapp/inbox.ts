import fs from 'fs'
import path from 'path'

export interface InboxEntry {
  content: string
  meta: { chat_id: string; sender: string }
}

export interface McpServer {
  notification(params: { method: string; params: unknown }): Promise<void>
}

export function inboxWrite(entry: InboxEntry, inboxDir: string): string {
  const file = path.join(inboxDir, `${Date.now()}-${Math.random().toString(36).slice(2)}.json`)
  fs.writeFileSync(file, JSON.stringify(entry))
  return file
}

export function inboxDelete(file: string): void {
  try { fs.unlinkSync(file) } catch {}
}

export function inboxReadAll(inboxDir: string): Array<{ file: string; entry: InboxEntry }> {
  try {
    return (fs.readdirSync(inboxDir) as string[])
      .filter(f => f.endsWith('.json'))
      .sort()
      .map(f => {
        const file = path.join(inboxDir, f)
        try {
          const entry = JSON.parse(fs.readFileSync(file, 'utf-8') as string) as InboxEntry
          return { file, entry }
        } catch {
          inboxDelete(file)
          return null
        }
      })
      .filter(Boolean) as Array<{ file: string; entry: InboxEntry }>
  } catch {
    return []
  }
}

export async function sendNotification(
  mcp: McpServer,
  entry: InboxEntry,
  inboxFile?: string,
): Promise<boolean> {
  try {
    await mcp.notification({
      method: 'notifications/claude/channel',
      params: { content: entry.content, meta: entry.meta },
    })
    if (inboxFile) inboxDelete(inboxFile)
    return true
  } catch {
    return false
  }
}

export async function drainInbox(inboxDir: string, mcp: McpServer): Promise<void> {
  const pending = inboxReadAll(inboxDir)
  for (const { file, entry } of pending) {
    process.stderr.write(`[whatsapp] Replaying queued message from ${path.basename(file)}\n`)
    const ok = await sendNotification(mcp, entry, file)
    if (!ok) {
      process.stderr.write(`[whatsapp] Replay failed, will retry\n`)
    }
  }
}

export function startDrainLoop(inboxDir: string, mcp: McpServer): ReturnType<typeof setInterval> {
  return setInterval(async () => {
    const pending = inboxReadAll(inboxDir)
    for (const { file, entry } of pending) {
      const ok = await sendNotification(mcp, entry, file)
      if (!ok) break
    }
  }, 1000)
}
