# Architecture

## System purpose

TebexPurchaseCheck is a Discord slash-command bot that lets trusted staff verify Tebex transaction and purchase-history records without leaving Discord.

The app is intentionally small and should stay boring, explicit, and easy to operate. It should not become a general-purpose economy/admin bot unless the architecture is split into modules first.

## Runtime model

```text
Discord staff user
  -> slash command
  -> discord.py interaction handler
  -> staff authorization check
  -> TebexClient aiohttp request
  -> defensive payload normalization
  -> Discord embed/page/attachment response
```

## External systems

| System | Direction | Purpose |
| --- | --- | --- |
| Discord | inbound and outbound | Staff slash commands, embeds, pagination buttons, receipt attachment delivery. |
| Tebex Plugin API | outbound | Transaction and user purchase-history lookup. |
| Environment variables | inbound at startup | Secrets, guild ID, role IDs, pagination settings, logging level. |

## Configuration boundary

The app reads configuration from environment variables at startup:

- `GUILD_ID`: Discord server/guild where slash commands should sync.
- `TEBEX_SECRET`: Tebex Plugin API secret.
- `DISCORD_TOKEN`: Discord bot token.
- `STAFF_ROLE_IDS`: comma-separated Discord role IDs that may run receipt commands.
- `HISTORY_ITEMS_PER_PAGE`: payment rows per embed page, clamped to 1-15.
- `LOG_LEVEL`: Python logging level.

Configuration is loaded once at import/startup. A missing required value fails fast.

## Security boundary

The bot treats Tebex purchase data as staff-only operational data.

Authorization passes if the Discord user is one of:

- server administrator;
- has `Manage Server`;
- has a role listed in `STAFF_ROLE_IDS`.

All unauthorized responses are private. Purchase history is private by default even for authorized staff.

## Command architecture

### `/transaction`

Flow:

1. Defer the Discord interaction privately.
2. Check staff authorization.
3. Fetch `/payments/{transaction_id}` from Tebex.
4. Normalize player, currency, packages, and notes.
5. Send a compact transaction embed.

### `/purchasehistory`

Flow:

1. Determine whether response should be private.
2. Defer the Discord interaction.
3. Check staff authorization.
4. Fetch `/user/{uuid}` from Tebex.
5. Normalize payments.
6. Sort payments newest-first.
7. Build embed pages.
8. Build complete `.txt` receipt attachment.
9. Send first embed, navigation view, and receipt attachment.

## Pagination design

Discord has strict message/embed limits. The app avoids those limits with two layers:

1. Embed pagination for readable staff review.
2. Full `.txt` receipt attachment for complete audit review.

The attachment is the source of truth for staff decisions because it is not constrained by the same readability/page boundaries as embeds.

## Error handling design

Tebex failures are mapped to staff-safe Discord messages:

| Condition | User-facing result |
| --- | --- |
| 404 | Tebex record/user was not found. |
| 401/403 | Tebex rejected configured secret. |
| 429 | Tebex rate limited the request. |
| non-2xx | Generic Tebex request failure. |
| invalid JSON | Tebex returned invalid response. |
| timeout | Tebex did not respond in time. |

Raw Tebex response bodies are logged only in truncated form and are not sent to Discord.

## Data storage

The app currently stores no persistent data.

This is good for privacy and simplicity, but it means there is no historical audit log of who checked which receipt. If staff accountability becomes important, add an audit log that records lookup metadata only:

- timestamp;
- Discord user ID;
- command name;
- lookup UUID/transaction ID;
- success/failure;
- payment count returned.

Avoid storing full receipt bodies unless there is a clear operational need and a retention policy.

## Future module split

When the app grows, split it into modules using this boundary:

```text
tebex_purchase_check/
  config.py          # env parsing and Settings
  tebex_client.py    # Tebex API wrapper and errors
  security.py        # staff authorization
  formatting.py      # money/date/status/payment formatting
  receipts.py        # page and txt receipt builders
  views.py           # Discord UI views/buttons
  commands.py        # slash command registration
  bot.py             # client setup/run
```

Keep command handlers thin. Business logic should live in formatting/client/security modules so it can be tested without Discord.
