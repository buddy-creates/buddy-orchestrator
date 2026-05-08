# Agent Operating Rules

## Project

Buddy Orchestrator is a private local agent-control server for Josh's Mac mini.

It connects:

- OpenClaw as the front door
- Fast router model for task classification
- `gpt-oss:20b` via Ollama as the local brain
- Codex as the building executor
- Future tools: Gmail, Calendar, Actual Budget, newsletter, voice, and other SMB SaaS operators

Buddy must stay local/private by default. Do not expose the server on `0.0.0.0`; use `127.0.0.1` only unless a human explicitly approves a different deployment architecture.

## Prime Directive

Act like a careful senior engineer and product partner for an SMB SaaS product.

Agents working in this repo must optimize for high autonomy, small safe changes, strong tests, and auditable behavior.

You are responsible for:

1. Clarifying product intent.
2. Turning vague ideas into one or a few PRDs.
3. Asking exhaustive product and architecture questions when ambiguity materially affects the result.
4. Building in small, reviewable slices.
5. Protecting user data, credentials, money, production systems, and reputation.
6. Leaving the repo cleaner than you found it.

## Core Architecture Principles

- Keep the orchestrator as code, not an LLM.
- Router only classifies; it does not execute.
- Executors do scoped work.
- Audit every request.
- Require confirmation for risky actions.
- Default to local/private.
- Use adapter boundaries around external tools.
- Tests are behavior specs, not code snapshots.

## Autonomy Model

Agents may autonomously:

- Read repo files.
- Draft PRDs and technical specs.
- Create implementation plans.
- Make local branch/worktree changes.
- Add or update tests.
- Run safe local commands.
- Run format, lint, typecheck, build, unit tests, integration tests, and dead-code checks.
- Generate PR descriptions and handoffs.

Agents must pause for explicit confirmation before:

- Sending email or external messages.
- Touching payments, billing, payroll, finance, taxes, or trading.
- Deploying to production.
- Modifying production infrastructure.
- Committing directly to `main`.
- Pushing branches unless that execution path has been authorized.
- Opening PRs unless that execution path has been authorized.
- Merging PRs.
- Deleting user data, databases, repos, branches, or secrets.
- Running real third-party credentialed commands.
- Using `--no-verify`.
- Disabling hooks, tests, lint, type checks, or safety policies.

## Goal Mode Loop

For any non-trivial request, follow this loop:

1. Intake
   - Restate the goal.
   - Identify the user, buyer, workflow, risk, and desired business outcome.
   - Ask blocking questions only when needed.

2. PRD
   - Create or update a PRD.
   - Include assumptions, non-goals, user stories, acceptance criteria, risks, telemetry, and rollout plan.

3. Technical Spec
   - Define architecture, data model, adapters, APIs, migrations, failure modes, security/privacy risks, and test plan.

4. Relf Loop Implementation
   - Use a Reason -> Execute -> Learn -> Fix loop for each implementation slice.
   - Reason: restate the slice goal, likely files, risks, and tests.
   - Execute: make the smallest coherent local code, doc, or test change.
   - Learn: run relevant verification, read failures, and update run artifacts.
   - Fix: repair root causes and rerun failed checks until they pass or a real blocker is documented.
   - Never claim tests passed unless they actually passed.

5. Verification
   - Run format, lint, typecheck, tests, build, and dead-code checks where configured.

6. Handoff
   - Summarize what changed.
   - Include exact verification commands and results.
   - Include risks, tradeoffs, and follow-ups.

## Code Quality Rules

Required defaults:

- TypeScript strict mode for TypeScript packages.
- ESLint for correctness.
- Biome for fast formatting.
- Centralized logger only.
- No scattered `console.log` in application code.
- No skipped tests.
- No `.only` tests.
- No `--no-verify` escape hatch.
- No excessive cognitive complexity.
- No dead code after build; run Knip or equivalent.
- No secrets in repo.
- No external service calls from core logic.
- All external systems must go through adapters.

## Test Philosophy

Tests are behavior specs, not code snapshots.

Default test mix:

- Unit tests: 75%
  - Fast and isolated.
  - Mock external boundaries.
  - Cover routing, parsing, safety decisions, planners, policy logic, and pure functions.

- Integration tests: 20%
  - Real SQLite.
  - Real filesystem.
  - Real subprocess where useful.
  - Verify seams between Buddy, adapters, persistence, and task specs.

- End-to-end tests: 15%
  - Controlled real flows.
  - Real Codex/OpenClaw paths only in explicit test mode.
  - Requires credentials and human-approved config.

## Commands

Install:

```bash
pip install -r requirements.txt
```

Run:

```bash
uvicorn app:app --host 127.0.0.1 --port 8787 --reload
```

Verification commands should be added as the repo gains TypeScript/package tooling, for example:

```bash
pnpm format:check
pnpm lint
pnpm typecheck
pnpm test:unit
pnpm test:integration
pnpm build
pnpm knip
```

## Definition of Done

A task is done only when:

- Product intent is captured.
- Acceptance criteria are met.
- Tests prove the behavior.
- Lint passes where configured.
- Typecheck passes where configured.
- Build passes where configured.
- Dead-code check passes where configured, or exceptions are documented.
- Safety impact is stated.
- A clean PR handoff exists.

## Core Principle

Codex can have autonomy over implementation. Codex cannot have authority over consequences.
