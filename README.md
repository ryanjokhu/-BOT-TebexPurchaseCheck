# [BOT] TebexPurchaseCheck

A staff-only Discord bot for checking Tebex transactions and purchase history by SteamID64/UUID.

## What changed

The old bot cut off long purchase histories because it sent only the first 2,000 characters of the generated Discord message. This version sends purchase history as paginated Discord embeds and attaches the complete receipt as a `.txt` file, so staff can verify long-time players without guessing or waiting for an executive manual check.

## Commands

- `/transaction <transaction_id>` — fetch a single Tebex transaction.
- `/purchasehistory <uuid> [private]` — fetch a player's purchase history by SteamID64/UUID.
  - `private` defaults to `true`, so receipt lookups are visible only to the staff member who ran the command.
  - Set `private` to `false` only when staff intentionally want the receipt posted in the channel.

## Access control

The commands are available to:

- Discord server administrators.
- Users with the `Manage Server` permission.
- Users with a role ID listed in `STAFF_ROLE_IDS`.

If `STAFF_ROLE_IDS` is empty, only administrators and users with `Manage Server` can run the commands.

## Setup

1. Install Python 3.10+.
2. Clone the repository.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy the environment example:

```bash
cp .env.example .env
```

5. Fill in `.env`:

```env
GUILD_ID=your_discord_server_id
TEBEX_SECRET=your_tebex_secret
DISCORD_TOKEN=your_discord_bot_token
STAFF_ROLE_IDS=role_id_1,role_id_2
HISTORY_ITEMS_PER_PAGE=8
LOG_LEVEL=INFO
```

6. Run the bot:

```bash
python tebextransactioncheck.py
```

## Purchase history behavior

For long purchase histories, the bot now:

- Sorts payments newest-first.
- Splits payments into readable Discord embed pages.
- Adds Previous/Next buttons for navigation.
- Attaches a complete `.txt` receipt with every payment returned by Tebex.
- Shows summary data including total USD spend, payment count, ban count, and chargeback rate.

## Notes

This bot displays every payment returned by the Tebex user endpoint. If Tebex itself ever limits that endpoint server-side, the bot will still show the complete response it receives, but a future API migration would be needed to fetch deeper paginated Tebex history.
