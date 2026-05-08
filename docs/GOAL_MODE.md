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
10. Reflect on failures, gaps, and next fixes.
11. Prepare a PR handoff.

## Relf Loop Requirement

Goal Mode must use a Relf-style loop: **Reason -> Execute -> Learn -> Fix**.

This loop makes Codex autonomous over implementation while keeping consequences gated by Buddy.

For every implementation slice:

### 1. Reason

- Restate the goal for this slice.
- Identify files likely to change.
- Identify risks and tests needed.
- Decide the smallest safe change to make next.

### 2. Execute

- Make the smallest coherent code, doc, or test change.
- Keep changes local and scoped.
- Avoid unrelated refactors.
- Do not push, merge, deploy, send external messages, delete data, or use real credentials without confirmation.

### 3. Learn

- Run the relevant verification commands.
- Read failures carefully.
- Update `commands.log` and `verification.md`.
- Distinguish between code failures, missing credentials, environmental blockers, and safety blockers.

### 4. Fix

- If checks fail, fix the root cause.
- Re-run the failed checks.
- Repeat the loop until checks pass or a real blocker is documented.
- Do not stop after the first failed test unless the failure requires human input, credentials, production access, or safety confirmation.

Never claim tests passed unless they actually passed.

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

The Relf loop should update these artifacts as it works:

- `plan.md` records the current implementation slice and next step.
- `commands.log` records commands attempted and outputs/summaries.
- `verification.md` records checks run, failures, fixes, and final state.
- `handoff.md` records the final result, risks, limitations, and follow-ups.

## Principle

Codex can have autonomy over implementation. Codex cannot have authority over consequences.
