# Buddy + OpenClaw System Memory

This document captures the current architecture and mental model for the Buddy Orchestrator + OpenClaw project.

## Core Summary

Buddy Orchestrator is a private local FastAPI server running on Josh's Mac mini. Its job is to receive messages from OpenClaw, classify them, decide whether they are safe to execute, route them to the right executor, log everything, and require confirmation before risky work.

OpenClaw is the front door. It owns Telegram and the chat interface. Buddy does not own Telegram directly. Buddy exposes local HTTP endpoints that OpenClaw can call, and returns simple `reply_text` strings that OpenClaw can send back to the user.

The intended local server address is:

```text
http://127.0.0.1:8787
```

Buddy must stay local/private. Do not expose it on `0.0.0.0`.

## Main Actors

### OpenClaw

User-facing shell, currently Telegram-oriented. It receives user messages and commands, then forwards them to Buddy.

### Buddy Orchestrator

Local FastAPI control plane. It is code, not an LLM. It classifies, gates, dispatches, logs, and stores confirmations.

### Router

Classification layer only. It decides intent, executor, risk, complexity, and whether confirmation is needed. It never performs the requested work.

### `gpt_oss` executor

Local conversational brain. It calls Ollama at:

```text
http://127.0.0.1:11434
```

using `gpt-oss:20b` by default.

### `codex` executor

Code/build task pathway. Currently it creates a Codex task spec JSON under:

```text
agent-workspace/tasks/
```

and asks `gpt_oss` for a concise execution brief. It does not directly make code changes yet.

### `fallback` executor

Safe placeholder for unsupported or future tools such as Gmail, Calendar, finance, deploy, payment, etc. It logs the request but takes no external action.

### SQLite audit/confirmation store

Buddy creates `audit.db`, containing:

- `audit_log`
- `pending_confirmations`

## Normal Message Flow

A user sends a message to OpenClaw, for example:

```text
hello
what is this project?
```

OpenClaw forwards the text to Buddy:

```http
POST /openclaw/message
```

```json
{
  "text": "...",
  "channel": "telegram",
  "user_id": "...",
  "chat_id": "..."
}
```

Buddy internally handles this the same way as:

```http
POST /message
```

Buddy calls the router.

The router returns a structured route like:

```json
{
  "intent": "question",
  "executor": "gpt_oss",
  "risk": "low",
  "needs_confirmation": false,
  "complexity": "low",
  "reason": "General question or chat should go to the local gpt-oss brain."
}
```

Because this is low risk, Buddy dispatches immediately to `gpt_oss`.

`gpt_oss` calls Ollama's `/api/generate`.

Buddy logs the request, route, executor, output text, latency, and timestamp.

Buddy returns:

```json
{
  "reply_text": "...",
  "confirmation_required": false,
  "confirmation_id": null,
  "commands": []
}
```

OpenClaw sends `reply_text` back to the user in Telegram.

## Risky Or Code Task Flow

For a request like:

```text
build me an expense dashboard
```

the router forces it into the Codex path:

```json
{
  "intent": "code_task",
  "executor": "codex",
  "risk": "medium",
  "needs_confirmation": true,
  "complexity": "standard",
  "reason": "Code/build tasks may modify files, so they require confirmation before execution."
}
```

Buddy does not execute it immediately.

Instead, Buddy creates a row in `pending_confirmations`, returns a `confirmation_id`, and gives OpenClaw Telegram-friendly commands:

```text
Confirmation required before Buddy executes this request.
Confirmation ID: <uuid>
Approve: /approve <uuid>
Reject: /reject <uuid>
```

OpenClaw should display enough of that for the user to approve or reject.

## Approval Flow

When the user sends:

```text
/approve <confirmation_id>
```

OpenClaw calls:

```http
POST /openclaw/command
```

```json
{
  "command": "/approve <confirmation_id>",
  "user_id": "...",
  "chat_id": "..."
}
```

Buddy parses the command, loads the pending confirmation, marks it approved, and dispatches the original request to the stored executor.

For a Codex route, the current executor creates a task spec JSON file in:

```text
agent-workspace/tasks/
```

It also asks local `gpt_oss` to produce a concise execution brief for the future Codex builder.

After execution, Buddy marks the confirmation as executed and logs the whole sequence.

## Rejection Flow

When the user sends:

```text
/reject <confirmation_id>
```

Buddy marks the confirmation as rejected, does not dispatch the executor, logs the cancellation, and returns:

```text
Confirmation rejected; request cancelled.
```

## Safety Rules

Buddy's core safety model is:

- Low risk -> execute immediately
- Medium/high risk -> require confirmation
- Code/build tasks -> always medium risk and require confirmation
- Unsupported sensitive tools -> fallback, no external action

Buddy must not automatically send email, modify finance data, deploy, commit, push, trade, pay, delete, or perform destructive/external actions without confirmation and an implemented safe executor.

## Project / Planning Context

A newer Buddy planning layer treats GitHub as the cross-repo project registry.

Buddy can use a private GitHub token to inspect repositories visible to that token. Planning should use GitHub repositories, issues, pull requests, README files, and GitHub Projects as shared project state.

Local private state stays local:

- `.env`
- `audit.db`
- logs
- OpenClaw runtime state

## Important Mental Model

- OpenClaw is the mouth and ears.
- Buddy is the local nervous system.
- The router is the triage desk.
- Executors are scoped hands.
- SQLite is memory and audit trail.
- Ollama / `gpt-oss` is the local conversational brain.
- Codex is intended to become the builder, but the current Codex executor is still a queued task-spec stub rather than a full autonomous code-changing bridge.

## Current Implementation Status

The current Codex executor is not yet a full autonomous code-changing bridge. It is a queued task-spec creator that writes task JSON under `agent-workspace/tasks/` and produces an execution brief using local `gpt_oss`.

The next likely step is to turn the Codex executor from a stub into a real builder arm while preserving Buddy's confirmation gate and audit log.
