# Roadmap

## Current release goal

Ship the purchase-history cutoff fix safely:

- paginated Discord history;
- complete text receipt attachment;
- staff-only access;
- environment-based secrets;
- current-standard documentation;
- minimal CI syntax validation.

## P0: before merge

These are required before merging the draft PR into `master`:

1. Confirm CI passes.
2. Run local syntax check if testing manually:

```bash
python -m py_compile tebextransactioncheck.py
```

3. Test `/transaction` with a known valid transaction.
4. Test `/purchasehistory` with a short-history player.
5. Test `/purchasehistory` with a long-history player.
6. Confirm the `.txt` receipt contains all payments returned by Tebex.
7. Confirm a non-staff account is denied.
8. Confirm private mode is default.
9. Confirm `private=false` only posts publicly when intentionally selected.

## P1: highest-value next improvements

1. Add automated tests for receipt formatting and pagination.
2. Expand CI with linting and test execution.
3. Add persistent lookup audit logs.
4. Add a `/receiptfile <uuid>` command for file-only evidence.
5. Add a `PUBLIC_RECEIPTS_ENABLED=false` feature flag to disable `private=false` in stricter servers.

## P2: reliability improvements

1. Add retry logic for transient Tebex failures.
2. Add structured JSON logs.
3. Add a deployment guide for the exact production host/process manager.
4. Add dependency locking.
5. Add a small health/startup self-check.

## P3: product improvements

1. Add CSV receipt export.
2. Add package-name search inside purchase history.
3. Add staff-log channel summaries.
4. Add support for searching by known transaction ID and jumping to related player history.
5. Add safer receipt redaction modes for screenshots or public staff reports.

## P4: architecture improvements

Split the single runtime file into modules only when the app gains tests, audit storage, or more commands. Avoid unnecessary complexity while the bot remains small.

Potential module split:

```text
tebex_purchase_check/
  config.py
  tebex_client.py
  security.py
  formatting.py
  receipts.py
  views.py
  commands.py
  bot.py
```

## Open research item

Confirm whether `https://plugin.tebex.io/user/{uuid}` returns true lifetime purchase history for long-history users or whether Tebex caps the response internally. The current fix guarantees Discord no longer truncates output, but only live Tebex testing can prove that the endpoint returns every historical payment.
