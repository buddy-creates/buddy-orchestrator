# Codex Goal Mode

Goal Mode turns Codex from a task executor into a product-building partner.

The goal is high autonomy with hard safety rails.

## What Goal Mode Does

Given a high-level user request, Goal Mode should:

1. Understand the product outcome.
2. Ask missing product questions when needed.
3. Draft one or more PRDs.
4. Draft a technical spec.
5. Break the work into implementation slices.
6. Create a branch/worktree when authorized by the local executor.
7. Implement the smallest safe slice.
8. Add behavior-focused tests.
9. Run verification.
10. Prepare a PR handoff.

## What Goal Mode Must Not Do Without Confirmation

Goal Mode must not:

- Deploy.
- Merge.
- Push if not authorized.
- Delete data.
- Send messages externally.
- Touch production systems.
- Touch money, billing, finance, payroll, tax, or trading systems.
- Use real credentials without explicit test-mode approval.
- Bypass hooks with `--no-verify`.

## Ideal Task Shape

Good:

```text
Build an expense dashboard for SMB operators that imports CSV expenses, categorizes them, and shows monthly burn by vendor/category.
```

Bad:

```text
Make my business app better.
```

When the task is vague, Goal Mode should produce questions and a draft PRD first.

## Autonomy Levels

### Level 0: Read-only Advisor

Can inspect repo and propose plans.

### Level 1: Local Planner

Can create PRDs, issues, and task specs.

### Level 2: Local Builder

Can modify files locally, run tests, and prepare branch diffs.

### Level 3: PR Creator

Can push branches and open PRs only after confirmation.

### Level 4: Release Operator

Can deploy only with explicit confirmation and a dedicated release checklist.

Default should be Level 2 until the system is proven.

## Permission Matrix

| Action | Read-only | Local Planner | Local Builder | PR Creator | Release Operator |
|---|---:|---:|---:|---:|---:|
| Read files | yes | yes | yes | yes | yes |
| Draft PRDs/specs | yes | yes | yes | yes | yes |
| Edit files locally | no | no | yes | yes | yes |
| Run unit tests | yes | yes | yes | yes | yes |
| Run integration tests | no | yes | yes | yes | yes |
| Run e2e tests with real credentials | no | no | confirm | confirm | confirm |
| Push branch | no | no | no | confirm | confirm |
| Open PR | no | no | no | confirm | confirm |
| Merge PR | no | no | no | no | confirm |
| Deploy | no | no | no | no | confirm |
| Delete data | no | no | no | no | confirm |

## Run Artifacts

Every Codex Goal Mode run should leave structured local artifacts:

```text
agent-workspace/runs/<run_id>/
  request.json
  route.json
  prd.md
  tech-spec.md
  plan.md
  commands.log
  verification.md
  handoff.md
```

These artifacts make each run inspectable, resumable, and auditable.

## Principle

Codex can have autonomy over implementation. Codex cannot have authority over consequences.
