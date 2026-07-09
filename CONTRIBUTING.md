# Contributing

## Change standard

This bot affects staff payment-verification decisions, so changes should be review-first and easy to roll back.

Do not push directly to `master` for functional changes. Use a branch and pull request.

## Before changing code

1. Read `MANIFEST.md`.
2. Read the relevant docs in `/docs`.
3. Understand whether the change affects receipt accuracy, privacy, permissions, or Tebex API behavior.
4. Prefer small, obvious changes over clever rewrites.

## Branch naming

Use clear branch names:

```text
fix/<short-problem>
feature/<short-feature>
docs/<short-doc-change>
security/<short-security-change>
```

Examples:

```text
fix/full-purchase-history-pagination
docs/staff-guide
security/audit-logging
```

## Required validation

Before opening or updating a PR:

```bash
python -m py_compile tebextransactioncheck.py
```

For receipt/purchase-history changes, also manually test:

- one short-history player;
- one long-history player;
- staff authorization;
- non-staff denial;
- private default behavior;
- receipt attachment contents.

## Pull request requirements

Every PR should include:

- Summary of what changed.
- Why the change is needed.
- Validation performed.
- Risks or limitations.
- Rollback notes.

## Coding standards

- Keep code explicit and readable.
- Do not hide payment/receipt behavior behind vague abstractions.
- Do not log secrets.
- Do not send raw Tebex response bodies to Discord.
- Treat receipt data as staff-only.
- Keep command handlers thin when possible.
- Add tests before large refactors.

## Documentation standard

Update docs when a change affects:

- setup;
- deployment;
- staff workflow;
- security/privacy;
- command behavior;
- environment variables;
- verification or rollback.

## Merge standard

Do not merge until:

- syntax checks pass;
- relevant manual Discord/Tebex test passes;
- docs are updated;
- rollback path is clear.
