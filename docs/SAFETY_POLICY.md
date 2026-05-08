# Safety Policy

Buddy and Codex must classify every action by risk.

## Low Risk

May execute immediately.

Examples:

- Read local repo files.
- Generate plans.
- Draft PRDs.
- Run unit tests.
- Run typecheck.
- Run formatter.
- Read local SQLite test DB.
- Create local task specs.

## Medium Risk

Requires confirmation depending on route.

Examples:

- Modify repo files.
- Create branches.
- Generate migrations.
- Run integration tests with subprocesses.
- Create local database files.
- Draft GitHub issues or PRs.

## High Risk

Always requires explicit confirmation.

Examples:

- Send emails.
- Send Telegram messages outside the current chat.
- Deploy.
- Merge PRs.
- Push to protected branches.
- Delete data.
- Modify billing, payroll, tax, bank, or finance data.
- Use real customer credentials.
- Run production migrations.

## Forbidden Without Dedicated Executor

Until a safe executor exists, route to fallback:

- Email send
- Calendar edits
- Finance changes
- Billing changes
- Production deploys
- Payments
- Data deletion

## Confirmation UX

When confirmation is required, Buddy should return a clear approval/rejection path:

```text
Confirmation required before Buddy executes this request.
Confirmation ID: <uuid>
Approve: /approve <uuid>
Reject: /reject <uuid>
```

## Audit Requirements

Every routed request should record:

- input_text
- route_json
- executor
- risk
- needs_confirmation
- confirmation_id when applicable
- result
- latency_ms
- timestamp
- error details when applicable
