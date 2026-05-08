# Buddy Orchestrator

Buddy Orchestrator is a private local FastAPI server for routing OpenClaw messages to local executors on Josh's Mac mini.

It currently supports:
- `POST /message` to classify and execute a message.
- `POST /confirm` to approve or reject a pending confirmation.
- `GET /confirmations` to inspect pending/recent confirmations.
- `GET /github/status` to verify Buddy's private GitHub credential.
- `GET /projects` to list GitHub repositories visible to Buddy's token.
- `GET /planning/context` to explain Buddy's GitHub-backed cross-repo planning model.
- `POST /openclaw/message` for Telegram-friendly OpenClaw messages.
- `POST /openclaw/command` for `/approve` and `/reject` commands from OpenClaw.
- `POST /route` to inspect router output without executing the chosen executor.
- `GET /health` for a local health check.
- `GET /audit` to inspect the last 10 `audit_log` rows.
- SQLite audit logging to `audit.db`.
- Router providers: local mock by default, OpenAI strict JSON router when enabled.
- A local `gpt-oss:20b` executor through Ollama.
- A Codex executor stub for confirmed code tasks.

No Docker, Gmail, calendar, or finance tools are included yet.

## Install

```bash
pip install -r requirements.txt
```

## Environment

Create a local `.env` file:

```bash
cp .env.example .env
```

Mock routing is the default:

```bash
ROUTER_PROVIDER=mock
```

To use the OpenAI router provider:

```bash
ROUTER_PROVIDER=openai
OPENAI_API_KEY=your-api-key
OPENAI_ROUTER_MODEL=gpt-4o-mini
```

If the OpenAI router call fails or `OPENAI_API_KEY` is missing, Buddy falls back to the mock router.

## Run

```bash
uvicorn app:app --host 127.0.0.1 --port 8787 --reload
```

Do not run this server on `0.0.0.0`. Buddy is intended to stay private and local.

## Try It

Health:

```bash
curl http://127.0.0.1:8787/health
```

Normal message:

```bash
curl -X POST http://127.0.0.1:8787/message \
  -H "Content-Type: application/json" \
  -d '{"text":"hello"}'
```

Route debugging for a code task:

```bash
curl -X POST http://127.0.0.1:8787/route \
  -H "Content-Type: application/json" \
  -d '{"text":"build me a dashboard"}'
```

Message for a code task:

```bash
curl -X POST http://127.0.0.1:8787/message \
  -H "Content-Type: application/json" \
  -d '{"text":"build me a dashboard"}'
```

Approve a confirmation:

```bash
curl -X POST http://127.0.0.1:8787/confirm \
  -H "Content-Type: application/json" \
  -d '{"confirmation_id":"paste-id-here","approved":true}'
```

Reject a confirmation:

```bash
curl -X POST http://127.0.0.1:8787/confirm \
  -H "Content-Type: application/json" \
  -d '{"confirmation_id":"paste-id-here","approved":false}'
```

Recent confirmations:

```bash
curl http://127.0.0.1:8787/confirmations
```

OpenClaw Telegram-style message:

```bash
curl -X POST http://127.0.0.1:8787/openclaw/message \
  -H "Content-Type: application/json" \
  -d '{"text":"build me an expense dashboard","channel":"telegram","user_id":"josh","chat_id":"123"}'
```

OpenClaw approval command:

```bash
curl -X POST http://127.0.0.1:8787/openclaw/command \
  -H "Content-Type: application/json" \
  -d '{"command":"/approve paste-id-here","user_id":"josh","chat_id":"123"}'
```

OpenClaw rejection command:

```bash
curl -X POST http://127.0.0.1:8787/openclaw/command \
  -H "Content-Type: application/json" \
  -d '{"command":"/reject paste-id-here","user_id":"josh","chat_id":"123"}'
```

Risky action confirmation:

```bash
curl -X POST http://127.0.0.1:8787/message \
  -H "Content-Type: application/json" \
  -d '{"text":"send email to Sam"}'
```

Recent audit rows:

```bash
curl http://127.0.0.1:8787/audit
```

GitHub account status:

```bash
curl http://127.0.0.1:8787/github/status
```

GitHub-backed project registry:

```bash
curl http://127.0.0.1:8787/projects
curl http://127.0.0.1:8787/planning/context
```

Buddy uses GitHub as the cross-repo project registry. Repositories, issues,
pull requests, and GitHub Projects are the shared planning surface. Local files
such as `.env`, `audit.db`, logs, and OpenClaw runtime state stay private.

Expected router behavior:
- `"build me a dashboard"` routes to the `codex` executor with `intent: code_task`, `risk: medium`, and `needs_confirmation: true`.
- Normal questions route to the `gpt_oss` executor.
- Medium/high risk requests return `confirmation_required: true` and a `confirmation_id` from `/message`.

## Audit Log

Buddy creates `audit.db` in the project root. The `audit_log` table stores:
- `input_text`
- `route_json`
- `executor`
- `output_text`
- `latency_ms`
- `created_at`

Inspect `audit_log` with:

```bash
sqlite3 audit.db 'select id, executor, latency_ms, created_at from audit_log order by id desc limit 10;'
```

Inspect recent routes with:

```bash
sqlite3 audit.db 'select input_text, route_json from audit_log order by id desc limit 5;'
```

## Confirmations

Buddy creates a `pending_confirmations` table with:
- `id`
- `input_text`
- `route_json`
- `executor`
- `status`
- `created_at`
- `resolved_at`

Statuses are `pending`, `approved`, `rejected`, `executed`, and `failed`.

Inspect pending confirmations with:

```bash
sqlite3 audit.db "select id, executor, status, created_at from pending_confirmations order by created_at desc limit 10;"
```

## OpenClaw Bridge Scripts

These scripts call the local Buddy API and print only the Telegram reply text:

```bash
python scripts/openclaw_message.py "build me an expense dashboard"
python scripts/openclaw_command.py "/approve <id>"
python scripts/openclaw_command.py "/reject <id>"
```

OpenClaw still owns Telegram. Buddy only provides local HTTP endpoints and helper scripts.

## Configuration

Environment variables:
- `ROUTER_PROVIDER`, default `mock`; set to `openai` for the OpenAI router.
- `OPENAI_API_KEY`, required when `ROUTER_PROVIDER=openai`.
- `OPENAI_ROUTER_MODEL`, default `gpt-4o-mini`.
- `OLLAMA_HOST`, default `http://127.0.0.1:11434`
- `OLLAMA_MODEL`, default `gpt-oss:20b`
- `OLLAMA_TIMEOUT_SECONDS`, default `110`
- `OLLAMA_NUM_PREDICT`, default `1024`
- `BUDDY_AUDIT_DB`, default `audit.db`
- `BUDDY_GITHUB_TOKEN`, fine-grained GitHub token for Buddy's dedicated account.
- `BUDDY_GITHUB_OWNER`, optional default owner/org.
- `BUDDY_GITHUB_DEFAULT_REPO`, optional default repository.
- `BUDDY_GITHUB_API_URL`, default `https://api.github.com`

## Safety

Buddy will not automatically send email, modify finance data, deploy, or commit code. This version classifies, logs, calls local Ollama for normal chat, and blocks code/build tasks behind confirmation.
