# OpenClaw Buddy Bridge

OpenClaw owns Telegram. Buddy Orchestrator owns planning, routing, confirmations, and executor coordination.

Buddy must stay local at `http://127.0.0.1:8787`. Do not expose Buddy publicly and do not move Telegram bot credentials into Buddy.

## Message Flow

Normal Telegram messages:

```http
POST http://127.0.0.1:8787/openclaw/message
```

```json
{
  "text": "<telegram message text>",
  "channel": "telegram",
  "user_id": "<telegram user id>",
  "chat_id": "<telegram chat id>"
}
```

Buddy replies with:

```json
{
  "reply_text": "...",
  "confirmation_required": false,
  "confirmation_id": null,
  "commands": []
}
```

Confirmation commands:

```http
POST http://127.0.0.1:8787/openclaw/command
```

```json
{
  "command": "/approve <id>",
  "user_id": "<telegram user id>",
  "chat_id": "<telegram chat id>"
}
```

OpenClaw sends `reply_text` back to the Telegram chat.

## Repository Roles

- `buddy-orchestrator`: local private planning brain, GitHub registry reader, confirmation flow, executor routing.
- `openclaw`: Telegram receiver/sender and Buddy bridge client.

Keep runtime files local:

- `.env`
- `audit.db`
- logs
- Telegram session or bot credentials
- OpenClaw runtime state

## Next Integration Shape

The OpenClaw side should contain only a small Buddy client/helper:

- default `BUDDY_URL=http://127.0.0.1:8787`
- send `/approve` and `/reject` text to `/openclaw/command`
- send all other Telegram text to `/openclaw/message`
- return `reply_text` to Telegram

Do not add Gmail, calendar, finance, Docker, auth, or a second Telegram bot in Buddy for this bridge.
