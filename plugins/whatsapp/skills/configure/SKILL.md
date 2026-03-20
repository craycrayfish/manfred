---
name: configure
description: Set up the WhatsApp channel — show connection status, trigger QR re-auth, or logout.
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Bash(ls *)
  - Bash(mkdir *)
---

Manage WhatsApp channel configuration.

State directory: ~/.claude/channels/whatsapp/

Dispatch on $ARGUMENTS:
- No args or "status": Show connection status — check if auth/ dir exists and has creds.json, show dmPolicy and allowFrom count from access.json
- "qr": Explain that QR re-auth happens automatically on next launch. Delete the auth/ directory at ~/.claude/channels/whatsapp/auth/ so the next launch will prompt for QR scan.
- "logout": Delete ~/.claude/channels/whatsapp/auth/ entirely. Warn the user they will need to re-scan QR.

Always remind the user to add their phone number to the allowlist with /whatsapp:access allow +<phone> before the channel will accept messages.
