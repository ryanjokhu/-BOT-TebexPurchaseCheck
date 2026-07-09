# Operations Runbook

## Operating principle

This bot exists to support staff receipt verification. Operate it like a small production admin tool: secrets stay out of git, changes go through review, and long-history receipt behavior must be tested before deployment.

## Required environment

- Python 3.10+
- Discord bot token
- Discord server/guild ID
- Tebex Plugin API secret
- Staff role IDs, unless administrator/Manage Server access is enough

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

## Configure

Edit `.env`:

```env
GUILD_ID=your_discord_server_id
TEBEX_SECRET=your_tebex_secret
DISCORD_TOKEN=your_discord_bot_token
STAFF_ROLE_IDS=role_id_1,role_id_2
HISTORY_ITEMS_PER_PAGE=8
LOG_LEVEL=INFO
```

Never commit `.env`.

## Preflight checks

Run before starting the bot:

```bash
python -m py_compile tebextransactioncheck.py
python - <<'PY'
import os
required = ["GUILD_ID", "TEBEX_SECRET", "DISCORD_TOKEN"]
missing = [name for name in required if not os.getenv(name)]
print("missing=" + ",".join(missing) if missing else "env ok")
PY
```

If using `.env`, the second command does not automatically load it unless your shell exports it. The runtime bot does load `.env` when `python-dotenv` is installed.

## Start

```bash
python tebextransactioncheck.py
```

Successful startup should log that slash commands synced to the configured guild.

## Manual verification

Use a staff account:

1. Run `/transaction <known_transaction_id>`.
2. Confirm the result is private.
3. Confirm transaction fields are correct.
4. Run `/purchasehistory <short_history_steamid64>`.
5. Confirm the result includes a `.txt` receipt.
6. Run `/purchasehistory <long_history_steamid64>`.
7. Confirm multiple pages appear when applicable.
8. Click Previous/Next.
9. Open the `.txt` receipt and confirm no Discord cutoff.
10. Run `/purchasehistory <long_history_steamid64> private:false` only in a safe test channel.

Use a non-staff account:

1. Run `/transaction <known_transaction_id>`.
2. Confirm the response is unauthorized and private.
3. Run `/purchasehistory <known_steamid64>`.
4. Confirm the response is unauthorized and private.

## Production deployment notes

Recommended production process:

1. Pull the reviewed branch or merged commit.
2. Install dependencies in a clean virtual environment.
3. Place `.env` outside public/shared paths.
4. Start under a process manager such as `systemd`, `pm2`, Docker, or Pterodactyl, depending on the host.
5. Capture stdout/stderr logs.
6. Restrict filesystem permissions on `.env`.
7. Test one short-history and one long-history lookup after every deploy.

## Suggested systemd unit

Adjust paths and user before use:

```ini
[Unit]
Description=Tebex Purchase Check Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/tebex-purchase-check
EnvironmentFile=/opt/tebex-purchase-check/.env
ExecStart=/opt/tebex-purchase-check/.venv/bin/python /opt/tebex-purchase-check/tebextransactioncheck.py
Restart=always
RestartSec=10
User=tebexbot
Group=tebexbot
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

## Monitoring

Minimum log events to watch:

- startup and slash command sync;
- Tebex auth errors;
- Tebex rate limits;
- repeated timeouts;
- unexpected response-shape errors;
- Discord connection failures.

## Incident response

### Bot is offline

1. Check process manager status.
2. Check logs for missing env values.
3. Confirm Discord token is valid.
4. Confirm outbound network access to Tebex and Discord.
5. Restart the bot after fixing the root cause.

### Slash commands missing

1. Confirm `GUILD_ID` is correct.
2. Confirm the bot is invited to the correct server.
3. Restart the bot and watch for command sync logs.
4. Re-invite the bot if application command permissions are missing.

### Tebex lookups fail

1. Confirm `TEBEX_SECRET` is correct.
2. Confirm Tebex is reachable.
3. Check for rate limits.
4. Try a known valid transaction ID.
5. Rotate the secret if exposure is suspected.

### Purchase history still appears incomplete

1. Open the attached `.txt` receipt.
2. Count the payments in the attachment.
3. Compare that count to Tebex's admin dashboard for the same player.
4. If Tebex dashboard has more rows than the attachment, the current Tebex endpoint is likely returning a limited subset and needs a paginated/deeper API migration.
5. Do not grant disputed items until executive/admin dashboard confirmation.

## Rollback

Before merge:

- Do not merge the draft PR.
- Keep production on `master`.

After merge:

1. Identify the last known-good commit.
2. Revert the merge or deploy the previous commit.
3. Restart the bot.
4. Run `/transaction` and `/purchasehistory` smoke tests.
5. Keep the failed commit available for inspection.

## Release checklist

- Code reviewed.
- Documentation updated.
- `.env.example` still has no real secrets.
- `python -m py_compile tebextransactioncheck.py` passes.
- Manual Discord test passes.
- Long-history receipt test passes.
- Staff permission test passes.
- Rollback path known.
