# Adapter Architecture

Core orchestration code should not directly call external systems.

External capabilities must be wrapped behind adapters.

## Required Adapters

### LLMAdapter

Owns calls to Ollama, OpenAI, Anthropic, or local models.

### CodexAdapter

Owns Codex task creation, execution, status polling, PR creation, and artifact handoff.

### GitHubAdapter

Owns repo inspection, issue creation, PR creation, branch status, and project registry state.

### TelegramAdapter

Owns Telegram message formatting and delivery.

### EmailAdapter

Owns Gmail or SMTP actions.

### CalendarAdapter

Owns calendar actions.

### BillingAdapter

Owns Stripe or payment-provider actions.

### FinanceAdapter

Owns accounting, payroll, bank, or tax tools.

### FileSystemAdapter

Owns local file reads/writes.

### SubprocessAdapter

Owns shell commands.

### LoggerAdapter

Owns structured logging.

### SecretsAdapter

Owns environment variables and credential access.

## Rule

Application logic depends on interfaces, not vendor SDKs.

Bad:

```ts
await fetch("https://api.telegram.org/...")
```

Good:

```ts
await telegramAdapter.sendMessage(...)
```

## Why

Adapters allow:

- safer mocking
- behavior-focused tests
- centralized logging
- permission gates
- easier replacement
- better audits

## Test Expectations

- Unit tests should mock adapters.
- Integration tests should use real local adapters where safe.
- E2E tests should use real external adapters only in explicit test mode with approved credentials.
