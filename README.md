# TebexPurchaseCheck

A staff-only Discord bot for checking Tebex transactions and player purchase history by SteamID64/UUID.

This bot exists to stop receipt ambiguity. Staff should be able to verify a player's Tebex history directly from Discord without relying on player screenshots, partial messages, or executive-only manual checks.

## Current release focus

The legacy bot cut off long purchase histories because it generated one large Discord message and sent only the first 2,000 characters. This version fixes that by sending purchase history as paginated Discord embeds and attaching a complete `.txt` receipt containing every payment returned by Tebex.

## Commands

| Command | Purpose | Default visibility |
| --- | --- | --- |
| `/transaction <transaction_id>` | Fetch one Tebex transaction. | Private |
| `/purchasehistory <uuid> [private]` | Fetch a player's purchase history by SteamID64/UUID. | Private |

`/purchasehistory` supports `private=false`, but that should only be used intentionally in staff-only channels.

## Access control

Commands are available to:

- Discord server administrators;
- users with the `Manage Server` permission;
- users with a role ID listed in `STAFF_ROLE_IDS`.

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
SHOW_TOTAL_SPENT_IN_EMBED=false
LOG_LEVEL=INFO
```

6. Run the bot:

```bash
python tebextransactioncheck.py
```

## Purchase history behavior

For long purchase histories, the bot now:

- sorts payments newest-first;
- prioritizes product/package names in the visible Discord rows;
- uses the transaction ID as secondary audit detail, not the main row label;
- fetches individual Tebex transaction details when the user-history response does not include product names;
- splits payments into readable Discord embed pages;
- adds Previous/Next buttons for navigation;
- attaches a complete `.txt` receipt with every payment returned by Tebex;
- hides total spent from the visible embed by default while keeping it in the attached staff receipt.

The embed pages are for browsing. The `.txt` receipt is the audit artifact staff should use for final verification.

## Documentation

| Document | Purpose |
| --- | --- |
| [`MANIFEST.md`](MANIFEST.md) | Deep project manifest, production problem, changed files, verification, rollback. |
| [`docs/APP_AUDIT.md`](docs/APP_AUDIT.md) | Full app audit, risk register, acceptance checklist, merge recommendation. |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Runtime model, command flows, data boundaries, future module split. |
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | Setup, deployment, monitoring, incident response, rollback. |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Secrets, access control, privacy defaults, incident response. |
| [`docs/STAFF_GUIDE.md`](docs/STAFF_GUIDE.md) | Staff-facing command usage and receipt verification workflow. |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Prioritized next steps and open Tebex endpoint research item. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Branch, PR, validation, coding, and documentation standards. |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | Pull-request syntax validation workflow. |

## Validation before merge

CI now runs a Python syntax check on pull requests. Before merging/deploying this release, confirm CI passes and run this locally if needed:

```bash
python -m py_compile tebextransactioncheck.py
```

Then manually test:

- `/transaction` with a known valid transaction;
- `/purchasehistory` with a short-history player;
- `/purchasehistory` with a long-history player;
- product names appear in history rows when Tebex exposes them through the transaction detail endpoint;
- receipt attachment contents;
- staff authorization;
- non-staff denial;
- private default behavior.

## Known limitation

This bot displays every payment returned by the current Tebex `/user/{uuid}` endpoint. If Tebex itself limits that endpoint server-side, the bot will still show the complete response it receives, but a future API migration would be needed to fetch deeper paginated Tebex history.
