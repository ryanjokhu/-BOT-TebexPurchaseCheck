# Staff Guide

## What this bot is for

Use TebexPurchaseCheck when a player claims they purchased something, lost a package, needs a receipt checked, or has a long purchase history that is hard to verify manually.

The goal is simple: staff should make grant/refund/support decisions from Tebex data, not from player screenshots or memory.

## Commands

### `/transaction <transaction_id>`

Use this when you already have a Tebex transaction ID.

Expected result:

- player name/UUID;
- amount;
- status;
- date;
- purchased packages;
- notes if available.

### `/purchasehistory <uuid> [private]`

Use this when you need a player's complete purchase history by SteamID64/UUID.

Default behavior:

- `private=true`, visible only to you.
- The bot sends a summary embed.
- The bot attaches a complete `.txt` receipt.
- If there are many payments, the embed has Previous/Next buttons.

Only set `private=false` in a staff-only channel when you intentionally want other staff to see the receipt.

## How to verify a claim

1. Ask for the player's SteamID64/UUID or transaction ID.
2. Run `/purchasehistory <steamid64>`.
3. Open the attached `.txt` receipt.
4. Search inside the receipt for package names, transaction IDs, amounts, or dates.
5. Compare the claim to the receipt.
6. If the receipt does not show the claimed purchase, do not grant the item/package without escalation.
7. If the player disputes the result, escalate with the `.txt` receipt attached.

## Long-history players

For players with many purchases, do not rely only on the visible Discord embed page. The embed is for browsing. The attached `.txt` file is the complete staff receipt for everything Tebex returned.

Use the buttons to browse quickly, then use the file for final confirmation.

## Status meanings

Common statuses may include:

- `Complete`: payment appears completed.
- `Pending`: payment is not fully complete.
- `Refunded`: payment was refunded.
- `Chargeback`: payment was charged back/disputed.
- `Declined`: payment did not complete.

Do not grant packages from pending, refunded, chargeback, or declined transactions unless an executive explicitly approves.

## When to escalate

Escalate to an executive/admin when:

- the player claims a purchase that is not in the receipt;
- Tebex returns an error for a known valid player;
- the attached receipt count looks lower than the Tebex admin dashboard;
- there is a refund/chargeback conflict;
- the player has a complicated package history;
- the staff team is unsure whether to grant something.

## What not to do

- Do not accept cropped screenshots as proof when the bot can check Tebex.
- Do not post receipt files in public player channels.
- Do not share Tebex secrets or Discord bot tokens.
- Do not grant from partial evidence when the receipt does not support the claim.
- Do not bypass the bot for long-history players unless Tebex itself needs manual dashboard verification.

## Recommended staff note format

When acting on a receipt, leave a note like:

```text
Verified via /purchasehistory on YYYY-MM-DD.
SteamID64: <id>
Transaction/receipt evidence: <transaction id or receipt line>
Action taken: <grant/refund/deny/escalate>
Staff: <name>
```

## Troubleshooting

### Bot says unauthorized

You do not have admin, Manage Server, or a role listed in `STAFF_ROLE_IDS`. Ask an admin to confirm your access.

### Bot says Tebex record not found

Check that the SteamID64/UUID or transaction ID is correct. If correct, escalate.

### Receipt seems incomplete

Open the `.txt` file first. If the file is also missing known Tebex dashboard entries, escalate. The Discord cutoff is fixed, so this would likely mean Tebex returned a limited response or the lookup ID is wrong.

### Buttons stop working

The pagination view times out after several minutes. Run the command again if you need to continue browsing.
