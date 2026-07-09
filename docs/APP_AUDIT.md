# App Audit

Audit date: 2026-07-09
Repository: `ryanjokhu/-BOT-TebexPurchaseCheck`
Branch audited: `fix/full-purchase-history-pagination`
Default branch: `master`

## Executive summary

TebexPurchaseCheck is a small Discord staff bot that verifies Tebex transactions and player purchase history. The app is intentionally narrow: it exists to reduce receipt fraud, remove manual executive bottlenecks, and give staff a reliable way to inspect Tebex purchase data from Discord.

The original app had one critical production defect: long purchase histories were truncated before Discord received them. The app now removes the Discord-side cutoff by splitting purchase history into paginated embeds and attaching a complete text receipt for every payment returned by Tebex.

## Current app inventory

| Area | Current state | Notes |
| --- | --- | --- |
| Runtime | Single Python file: `tebextransactioncheck.py` | Acceptable for current app size, but should be split if the bot grows. |
| Discord library | `discord.py` | Slash commands and button pagination. |
| HTTP client | `aiohttp` | Used for Tebex Plugin API calls. |
| Config | Environment variables with optional `.env` loading | Current standard for secrets. |
| Dependencies | `requirements.txt` | Version ranges are present, no lock file yet. |
| Documentation | README, manifest, and `/docs` set | Updated to review/operations/security standards. |
| Tests | None | Manual verification checklist exists; automated tests are recommended next. |
| CI | GitHub Actions syntax check | Runs dependency install and `python -m py_compile tebextransactioncheck.py`. |

## Critical defect found

### Receipt history truncation

The legacy app built one large purchase-history message and sent only the first 2,000 characters. That meant long-time players with many payments had incomplete history in Discord.

Impact:

- Staff could not verify the complete purchase history.
- Players could lie about old purchases or missing packages.
- Staff had to wait for an executive/manual Tebex lookup.
- Incorrect grants were possible when staff acted from partial information.

Resolution:

- The app now uses Discord embeds with Previous/Next pagination.
- The app attaches a complete `.txt` receipt with every payment returned by Tebex.
- The receipt attachment becomes the reliable audit artifact.

## Current command audit

### `/transaction <transaction_id>`

Purpose: inspect one Tebex transaction by ID.

Current behavior:

- Staff-only.
- Calls `/payments/{transaction_id}` on Tebex.
- Returns player, amount, status, date, packages, and notes in an embed.
- Handles not-found, auth, rate-limit, timeout, and malformed response cases.

Risk level: Low.

Remaining concerns:

- Transaction package/note formatting is limited by Discord embed field limits.
- No persistent staff audit log yet.

### `/purchasehistory <uuid> [private]`

Purpose: inspect a player purchase history by SteamID64/UUID.

Current behavior:

- Staff-only.
- Private by default.
- Calls `/user/{uuid}` on Tebex.
- Sorts returned payments newest-first.
- Paginates receipt display in embeds.
- Attaches a complete `.txt` receipt.
- Shows total USD spend, payment count, ban count, and chargeback rate.

Risk level: Medium-low.

Remaining concerns:

- The bot can only show what the Tebex endpoint returns. If Tebex caps the endpoint internally, a deeper/paginated Tebex API strategy is needed.
- No persistent staff audit log yet.
- No automated regression tests yet.

## Security audit

### Strengths

- Secrets moved out of source code and into environment variables.
- `.env` files are ignored by git.
- Commands are staff-gated.
- Receipt lookups are private by default.
- Tebex API failures do not leak full raw response bodies into Discord.

### Risks

| Risk | Severity | Current control | Recommended next step |
| --- | --- | --- | --- |
| Staff can intentionally post receipts publicly with `private=false` | Medium | Default is private | Train staff; consider removing public mode if abused. |
| No persistent audit log of receipt lookups | Medium | None | Add local/DB/Discord staff-log audit entry per lookup. |
| No dependency lock file | Low-medium | Version ranges | Add pinned lock or deployment image. |
| Limited CI coverage | Low-medium | Syntax compile workflow | Add unit tests, lint, and dependency scanning. |
| Tebex endpoint may have undocumented server-side limits | Unknown | Complete display of returned data | Verify with long-history real accounts; migrate endpoint if needed. |

## Reliability audit

Current improvements:

- Explicit timeout on Tebex calls.
- Defensive handling for malformed JSON.
- Defensive field access for player, payments, notes, and packages.
- Pagination avoids Discord message limits.
- Attachment avoids embed/readability limits.
- CI syntax check catches invalid Python before merge.

Remaining reliability work:

1. Add unit tests for payment normalization, formatting, page splitting, and receipt text generation.
2. Add a smoke-test command or startup self-check for required env variables.
3. Add lint/type checks to CI.
4. Add structured audit logging for all lookups.
5. Add a clearer deployment unit file or Docker option once production host is known.

## Maintainability audit

Current state is acceptable for a small bot, but the runtime file is now large enough that future growth should split it into modules.

Recommended future structure:

```text
tebex_purchase_check/
  __init__.py
  bot.py
  config.py
  tebex_client.py
  commands/
    transaction.py
    purchase_history.py
  formatting/
    payments.py
    receipts.py
  security.py
  logging.py
  views.py
```

Do not split the app only for aesthetics. Split it when adding new commands, persistent audit logs, tests, or multiple Tebex endpoint strategies.

## Product workflow audit

The staff workflow is now aligned with the operational goal:

1. Staff runs `/purchasehistory <steamid64>`.
2. Bot returns summary, paginated history, and full receipt attachment.
3. Staff validates claim against the attached receipt instead of player screenshots.
4. If the player disputes the result, staff escalates with the `.txt` receipt attached.
5. Executive review only happens for true Tebex/API ambiguity, not Discord cutoff.

## Acceptance checklist

This branch is acceptable to merge after these checks pass in the real Discord server:

- CI syntax check passes.
- A staff user can run `/transaction` successfully.
- A staff user can run `/purchasehistory` for a short-history player.
- A staff user can run `/purchasehistory` for a long-history player.
- Long-history embed pagination works.
- The attached `.txt` receipt includes all payments returned by Tebex.
- A non-staff user cannot run either command.
- `private=true` is private.
- `private=false` posts visibly only when intentionally selected.
- Bot logs do not expose secrets.

## Merge recommendation

Merge only after one real long-history Tebex account is tested. The code-level fix is straightforward and directly addresses the Discord cutoff, but the true end-to-end validation depends on live Tebex response behavior.
