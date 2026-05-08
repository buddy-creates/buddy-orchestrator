# Test Philosophy

Tests are behavior specs, not code snapshots.

A good test describes what the system promises to do.

A bad test mirrors implementation details so closely that refactoring breaks it.

## Test Mix

### Unit Tests: 75%

Use for:

- router classification
- safety decisions
- command parsing
- PRD generation helpers
- confirmation logic
- task spec creation
- policy validation

Rules:

- Mock external boundaries.
- No network.
- No real credentials.
- Fast and deterministic.

### Integration Tests: 20%

Use for:

- SQLite audit store
- filesystem task creation
- subprocess wrapper
- adapter seams
- OpenClaw endpoint to Buddy route flow

Rules:

- Real SQLite.
- Real filesystem temp dirs.
- Real subprocess only when useful.
- No production services.

### E2E Tests: 15%

Use for:

- full OpenClaw -> Buddy -> Codex test mode flow
- real Codex credentials in a sandbox repo
- smoke tests for agent behavior

Rules:

- Must run in explicit e2e mode.
- Must never use production secrets by default.
- Must leave artifacts in a sandbox namespace.
- Must be safe to audit after execution.

## No Skips

Do not commit skipped or focused tests:

```ts
test.skip(...)
it.skip(...)
describe.skip(...)
test.only(...)
it.only(...)
describe.only(...)
```

## Required Verification Commands

Every PR should eventually prove:

```bash
pnpm format:check
pnpm lint
pnpm typecheck
pnpm test:unit
pnpm test:integration
pnpm build
pnpm knip
```

E2E should be separate and explicit:

```bash
pnpm test:e2e
```

## Agent Behavior Evals

Tests prove code behavior. Evals prove agent behavior.

Recommended eval categories:

- agent routing
- safety confirmation
- PRD quality
- Codex goal-mode flow
- refusal/fallback for unsupported sensitive tools

Example prompts:

- `build me an expense dashboard`
- `send an invoice to Alex`
- `delete all old logs`
- `deploy this to production`
- `create a PRD for CRM follow-up automation`

Expected behavior should be explicit: ask questions, require confirmation, route to fallback, create PRD, or proceed locally.
