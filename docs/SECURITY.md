# Security and Privacy

## Data classification

TebexPurchaseCheck handles payment-related operational data. Treat transaction IDs, player purchase histories, chargeback information, ban counts, and receipt files as staff-only data.

The bot should never be used as a public player-facing receipt lookup tool.

## Secrets

Required secrets/configuration:

- `DISCORD_TOKEN`
- `TEBEX_SECRET`
- `GUILD_ID`
- `STAFF_ROLE_IDS`

Rules:

- Never commit real secrets.
- Never paste real secrets into screenshots, public tickets, Discord channels, or GitHub issues.
- Use `.env` locally and environment variables in production.
- Rotate `DISCORD_TOKEN` and `TEBEX_SECRET` if exposure is suspected.
- Keep `.env.example` realistic but fake.

## Access control

Commands are restricted to:

- Discord administrators;
- users with `Manage Server`;
- users with role IDs in `STAFF_ROLE_IDS`.

This is intentional. Receipt data can influence grants, refunds, bans, and staff decisions.

## Privacy defaults

`/purchasehistory` is private by default.

Staff can intentionally set `private=false`, but that should be reserved for controlled staff channels or cases where a visible audit trail is useful. Do not post receipt data in public player channels.

## Logging policy

Current runtime logs are minimal and do not intentionally send raw Tebex responses to Discord.

Recommended logging policy:

- Log command name, staff user ID, lookup key, success/failure, and payment count.
- Do not log full payment histories by default.
- Do not log Discord tokens or Tebex secrets.
- Truncate unexpected Tebex response bodies if logging them for debugging.
- Store logs in a staff/admin-access-only location.

## Staff misuse controls

Risk: a staff member can look up private purchase histories unnecessarily.

Recommended controls:

1. Add persistent audit logging.
2. Periodically review lookup logs.
3. Keep `STAFF_ROLE_IDS` narrow.
4. Remove access from inactive or junior staff.
5. Keep public posting disabled by policy unless needed.

## Discord permissions

The bot needs enough permission to:

- register slash commands;
- send messages;
- send embeds;
- attach files;
- use buttons/components.

Avoid granting broad moderation/admin permissions to the bot unless your deployment process requires it. Server admins/users are checked through Discord member permissions, not bot permissions.

## Tebex access

Use a Tebex secret scoped for the minimum needed bot behavior when possible. If Tebex only provides a broad plugin secret, treat the bot host as sensitive infrastructure.

## Incident response

### Secret exposure

1. Revoke/rotate the exposed Discord token or Tebex secret.
2. Update production `.env` or secret store.
3. Restart the bot.
4. Review recent logs for unusual lookups.
5. Remove exposed secret from git history if it was committed.

### Unauthorized lookup concern

1. Remove the user's staff role immediately.
2. Check Discord permission changes.
3. Review bot logs if available.
4. Reissue `STAFF_ROLE_IDS` with only trusted roles.
5. Consider adding persistent audit logging before re-expanding staff access.

### Receipt data posted publicly

1. Delete the public Discord message if possible.
2. Remind staff that receipt lookups are private by default for a reason.
3. Consider disabling or removing `private=false` if repeated.
4. Record the incident in staff notes.

## Secure-by-default backlog

Highest value next security upgrades:

1. Persistent lookup audit log.
2. Optional staff-log Discord channel for lookup summaries.
3. CI secret scanning.
4. Dependency vulnerability scan.
5. Public-mode feature flag, so `private=false` can be disabled completely.
6. Separate least-privileged production user/process.
