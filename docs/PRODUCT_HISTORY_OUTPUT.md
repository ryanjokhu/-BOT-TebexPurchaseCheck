# Product History Output

## Why this exists

The purchase-history command should help staff verify what a player bought. Transaction IDs are useful audit metadata, but they are not useful as the primary visible row label.

## Visible Discord rows

Purchase-history rows now prioritize the product/package name:

```text
1. VIP Rank
   2026-03-15 00:21:58 UTC | 12.50 USD | Complete | Txn: tbx-...
```

This keeps the staff workflow focused on what matters: what the player purchased.

## Product-name enrichment

Some Tebex user-history responses include transaction IDs but not package names. When that happens, the bot now attempts to fetch each individual transaction detail and extract product/package names from that response.

If Tebex does not expose a product name in either response, the row will show `Product unavailable` and keep the transaction ID for manual dashboard lookup.

## Donor-neutral display

The visible embed hides total spent by default. The full `.txt` receipt still includes total spent for staff/admin audit purposes.

Set this only if you intentionally want total spend visible in the Discord embed:

```env
SHOW_TOTAL_SPENT_IN_EMBED=true
```
