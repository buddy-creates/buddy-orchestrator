# Engineering Standards

## Language

Use TypeScript strict mode for TypeScript packages.

Recommended compiler expectations:

- `strict: true`
- `noUncheckedIndexedAccess: true`
- `exactOptionalPropertyTypes: true`
- `noImplicitOverride: true`
- `noFallthroughCasesInSwitch: true`
- `noUnusedLocals: true`
- `noUnusedParameters: true`

## Formatting

Use Biome for formatting.

## Linting

Use ESLint for correctness, complexity, import hygiene, unsafe patterns, and test rules.

## Logging

Use a centralized logger.

Do not use scattered `console.log` in application code.

Every log should include when possible:

- timestamp
- request_id
- actor_id
- channel
- route
- executor
- risk
- confirmation_id
- result
- latency_ms
- error_code
- external_side_effects

## Complexity

Prefer simple functions.

Split code when:

- branching is hard to read
- a function handles multiple responsibilities
- tests require excessive setup
- cognitive complexity grows too high

## Dead Code

Run Knip after builds where TypeScript/package tooling exists.

Dead code should be deleted unless there is a documented reason to keep it.

## Secrets

No secrets in git.

Use `.env.example` for names only.

Use secret scanning in CI when available.

Never log secrets.

## External Boundaries

No direct external calls in core logic.

Use adapters.

## Database Discipline

Use migrations for schema changes.

Rules:

- no manual schema drift
- migrations are append-only unless explicitly approved
- integration tests run against migrated SQLite
- seed data is explicit
- destructive migrations require confirmation

## Precommit and CI

Precommit hooks are helpful, but CI is the real enforcement layer.

CI should eventually block PRs unless these pass:

- format check
- lint
- typecheck
- unit tests
- integration tests
- build
- dead-code check
- secret scan
- no skipped/focused tests
