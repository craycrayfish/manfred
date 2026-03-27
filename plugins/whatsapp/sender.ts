import fs from 'fs'
import path from 'path'

export function resolveLid(lid: string, authDir: string): string | null {
  try {
    for (const file of fs.readdirSync(authDir) as string[]) {
      const m = file.match(/^lid-mapping-(\d+)\.json$/)
      if (!m) continue
      const stored = JSON.parse(fs.readFileSync(path.join(authDir, file), 'utf-8') as string)
      if (stored === lid) return `+${m[1]}`
    }
  } catch {}
  return null
}

export function extractSender(jid: string, authDir: string): string {
  if (jid.endsWith('@s.whatsapp.net')) {
    const raw = jid.replace('@s.whatsapp.net', '')
    return raw.startsWith('+') ? raw : `+${raw}`
  }
  if (jid.endsWith('@lid')) {
    const lid = jid.replace('@lid', '')
    const phone = resolveLid(lid, authDir)
    return phone ?? `lid:${lid}`
  }
  return jid
}
