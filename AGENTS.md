# AGENTS.md

## Project

Buddy Orchestrator is a private local agent-control server for Josh's Mac mini.

It connects:
- OpenClaw as the front door
- Fast router model for task classification
- gpt-oss:20b via Ollama as local brain
- Codex as the building executor
- Future tools: Gmail, Calendar, Actual Budget, newsletter, voice

## Principles

- Keep the orchestrator as code, not an LLM.
- Router only classifies; it does not execute.
- Executors do scoped work.
- Audit every request.
- Require confirmation for risky actions.
- Default to local/private.
- Do not expose server on 0.0.0.0.
- Use 127.0.0.1 only.

## Commands

Install:

```bash
pip install -r requirements.txt
```

Run:

```bash
uvicorn app:app --host 127.0.0.1 --port 8787 --reload
```
