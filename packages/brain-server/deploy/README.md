# Deploying brain-server on the Mac mini

The brain runs as a launchd user agent on the Mac mini (`m4-mini`, SSH alias
`jarvis`), reachable only over the Tailscale tailnet. The Obsidian vault on the
mini's **local disk** is the source of truth; the SQLite index under
`.brain/index.db` is derived and disposable.

## One-time setup (on the mini, over `ssh jarvis`)

1. **Create the vault** from the template and put it under version control:

   ```bash
   cp -R packages/brain-server/vault-template ~/brain-vault
   cd ~/brain-vault && git init && git add -A && git commit -m "init brain vault"
   ```

2. **Install deps** in the server package:

   ```bash
   cd packages/brain-server && uv sync
   ```

3. **Generate a token** and keep it out of git (used by every client too):

   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

4. **Edit the plist** `deploy/com.manfred.brain.plist`:
   - set `BRAIN_VAULT` to `/Users/jarvis/brain-vault`
   - set `BRAIN_TOKEN` to the generated token
   - set `BRAIN_HOST` to the mini's **tailnet IP** (or `127.0.0.1` to keep it
     loopback-only and reach it via an SSH tunnel). **Never `0.0.0.0`.**
   - set `WorkingDirectory` to the absolute path of `packages/brain-server`

5. **Load it:**

   ```bash
   launchctl bootstrap gui/$(id -u) deploy/com.manfred.brain.plist
   launchctl kickstart -k gui/$(id -u)/com.manfred.brain
   ```

6. **Verify locally on the mini:**

   ```bash
   curl -H "Authorization: Bearer $BRAIN_TOKEN" http://localhost:8765/healthz
   ```

## From another tailnet device

Set `plugins/brain/brain.local.json` (gitignored) to:

```json
{ "url": "http://m4-mini:8765", "token": "<same token>" }
```

then:

```bash
plugins/brain/bin/brain health
```

## Operations

- **Logs:** `~/.brain/log/brain.out.log`, `~/.brain/log/brain.err.log`.
- **Rebuild the index** (DB is disposable): `brain` has no rebuild route yet in
  the MVP — delete `~/brain-vault/.brain/index.db` and restart; the server
  rebuilds from the vault on boot.
- **Backups:** daily `git -C ~/brain-vault add -A && git commit` (cron); the
  index needs no backup.
- **Bind safety:** the listener must stay on the tailnet/loopback. WireGuard
  encrypts tailnet traffic, so plain HTTP is acceptable inside it.
