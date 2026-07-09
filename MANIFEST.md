# TebexPurchaseCheck Deep Manifest

## Purpose

TebexPurchaseCheck is a Discord staff utility for R&R-style payment verification workflows. Its job is to let authorized staff verify Tebex receipts without relying on player screenshots, partial Discord messages, or executive-only manual checks.

## Primary production problem

The legacy `/purchasehistory` command fetched a Tebex user payload and generated one large text message. It then sent `response[:2000]`, which hard-truncated the message to Discord's normal message limit. Long-time players with many payments therefore had incomplete receipt histories in Discord, creating a staff-trust problem:

- staff could not see the full purchase history;
- players with long histories could claim missing purchases;
- staff had to wait for an executive/manual Tebex check;
- incorrect grants could happen when staff guessed from partial data.

## Repository state before update

- Default branch: `master`.
- Main runtime file: `tebextransactioncheck.py`.
- Documentation: basic README only.
- Dependency manifest: missing.
- Secret/config pattern: secrets were expected to be pasted directly into the script.
- Tests/CI: not present.
- Runtime architecture: single Python file using `discord.py` slash commands and `aiohttp`.

## Legacy command map

### `/transaction <transaction_id>`

Legacy behavior:

- Called `https://plugin.tebex.io/payments/{transaction_id}`.
- Displayed player, amount, date, status, packages, and notes.
- Sent one raw Discord text message.

Legacy risks:

- no staff permission gate;
- direct indexing could crash on unexpected payload shapes;
- no timeout-specific handling;
- secrets lived in source code placeholders.

### `/purchasehistory <uuid>`

Legacy behavior:

- Called `https://plugin.tebex.io/user/{uuid}`.
- Displayed username, total spent, ban count, chargeback rate, and payments.
- Sent `response[:2000]`.

Legacy risks:

- guaranteed truncation for long purchase histories;
- no pagination;
- no full receipt attachment/export;
- direct indexing could crash on missing payment fields;
- no staff permission gate;
- no clear distinction between complete Tebex response and Discord-display limit.

## New runtime behavior

### Full purchase-history delivery

The updated `/purchasehistory` command now:

- fetches the Tebex user payload;
- normalizes the returned payment records defensively;
- sorts payments newest-first;
- splits payments into Discord-safe embed pages;
- adds Previous/Next navigation buttons when more than one page exists;
- attaches a complete `.txt` receipt containing every payment returned by Tebex;
- shows summary fields for total USD spent, payment count, ban count, and chargeback rate.

The `.txt` receipt is the audit anchor. Even if the embed pages are inconvenient for a very long history, staff still receive a full downloadable receipt file.

### Privacy and staff workflow

`/purchasehistory` accepts a `private` option:

- `private=true` by default; receipt is only visible to the staff member running the lookup.
- `private=false` posts the receipt in-channel when staff intentionally need a visible audit trail.

Unauthorized users are always answered privately.

### Permission model

Commands are allowed for:

- Discord administrators;
- users with `Manage Server`;
- users whose role IDs are listed in `STAFF_ROLE_IDS`.

This prevents regular players from querying purchase records directly.

### Configuration model

Secrets and server IDs now come from environment variables instead of source code:

- `GUILD_ID`
- `TEBEX_SECRET`
- `DISCORD_TOKEN`
- `STAFF_ROLE_IDS`
- `HISTORY_ITEMS_PER_PAGE`
- `LOG_LEVEL`

`.env.example` documents the expected format. `.gitignore` blocks real `.env` files from being committed.

## Files added or changed

### `tebextransactioncheck.py`

Primary bot runtime. Reworked to include:

- environment-based settings;
- optional `.env` loading;
- Tebex API client wrapper;
- defensive JSON handling;
- rate-limit, auth, not-found, and generic error handling;
- staff authorization helper;
- transaction embed formatting;
- purchase-history pagination;
- complete text receipt attachment.

### `requirements.txt`

Pins the runtime dependency families:

- `discord.py`
- `aiohttp`
- `python-dotenv`

### `.env.example`

Documents required and optional runtime settings.

### `.gitignore`

Protects virtual environments, Python cache files, editor files, and local secret files.

### `README.md`

Updated setup, command, access-control, and purchase-history behavior documentation.

## Operational checklist

Before deployment:

1. Create a Discord bot token in the Discord Developer Portal.
2. Invite the bot with slash-command/application-command permissions.
3. Set `GUILD_ID` to the Discord server ID.
4. Set `TEBEX_SECRET` from the Tebex plugin/API secret.
5. Set `DISCORD_TOKEN` to the bot token.
6. Set `STAFF_ROLE_IDS` to the Discord role IDs allowed to run lookups.
7. Start with `HISTORY_ITEMS_PER_PAGE=8`.
8. Run `python -m py_compile tebextransactioncheck.py`.
9. Run the bot and confirm slash commands sync.
10. Test a short-history player and a long-history player.

## Verification checklist

Use a staff account:

- `/transaction <known_transaction_id>` returns a transaction embed.
- `/purchasehistory <known_short_history_uuid>` returns one page and a `.txt` receipt.
- `/purchasehistory <known_long_history_uuid>` returns multiple pages with Previous/Next buttons and a `.txt` receipt.
- The `.txt` file contains every payment visible in the Tebex response.
- `private=true` keeps the result visible only to the command runner.
- `private=false` posts the result in the channel.

Use a non-staff account:

- `/transaction` returns a private unauthorized message.
- `/purchasehistory` returns a private unauthorized message.
- Non-staff users cannot page through a posted purchase-history view.

## Remaining known limitation

The bot now avoids Discord-side truncation and displays every payment returned by the current Tebex user endpoint. If Tebex itself returns a limited subset of a player's lifetime purchases, then the next upgrade should migrate to a Tebex endpoint that supports explicit historical pagination or transaction search across all payments. That limitation cannot be proven from this repo alone because the legacy implementation only used `plugin.tebex.io/user/{uuid}`.

## Recommended future upgrades

1. Add structured logging to file or Discord staff-log channel.
2. Add a persistent audit log for who looked up which player and when.
3. Add a `/receiptfile <uuid>` command that only returns the full `.txt` receipt.
4. Add an optional CSV export for accounting/admin review.
5. Add unit tests around payment formatting and pagination boundaries.
6. Add GitHub Actions for syntax checks.
7. Consider a small SQLite cache only for audit metadata, not for secret payment data.
8. Rotate any Tebex/Discord secrets that were ever pasted into source code or shared in screenshots.

## Rollback plan

Because the update is isolated on a feature branch, rollback is simple:

- Do not merge the pull request if validation fails.
- Keep production pointed at `master` until a long-history test passes.
- If already deployed, redeploy the previous `master` commit and rotate secrets if needed.
