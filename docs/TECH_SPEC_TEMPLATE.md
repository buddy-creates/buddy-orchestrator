# Technical Spec Template

## Title

Short technical name.

## Related PRD

Link or reference the PRD.

## Summary

What are we building and why?

## Architecture

Describe the components involved and how data/control flows through them.

## Interfaces / Adapters

List every adapter touched:

- LLMAdapter
- CodexAdapter
- GitHubAdapter
- TelegramAdapter
- EmailAdapter
- CalendarAdapter
- BillingAdapter
- FinanceAdapter
- FileSystemAdapter
- SubprocessAdapter
- LoggerAdapter
- SecretsAdapter

## API Changes

Endpoints, request/response shapes, commands, or internal interfaces.

## Data Model

Tables, fields, migrations, indexes, and retention rules.

## Failure Modes

What happens when:

- Input is invalid
- External service fails
- Credentials are missing
- Filesystem is unavailable
- SQLite is locked
- Subprocess exits non-zero
- The agent produces incomplete output

## Security / Privacy

- Secrets involved
- PII involved
- Permission checks
- Data retention
- Logging redactions

## Observability

Required logs/metrics should include when possible:

- request_id
- actor_id
- channel
- route
- executor
- risk
- confirmation_id
- tool_calls
- latency_ms
- error_code
- external_side_effects

## Test Plan

### Unit Tests

Fast, isolated, mocked external boundaries.

### Integration Tests

Real SQLite, real filesystem, real subprocess where useful.

### E2E Tests

Controlled real agent flows in explicit test mode.

## Rollout Plan

- Local only
- Sandbox
- Staging
- Production

## Rollback Plan

How do we safely undo this?

## Open Questions

List unresolved technical questions.
