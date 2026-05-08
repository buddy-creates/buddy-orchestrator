from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


API_URL = "http://127.0.0.1:8787/openclaw/message"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/openclaw_message.py \"message text\"", file=sys.stderr)
        return 2

    payload = {
        "text": " ".join(sys.argv[1:]),
        "channel": "telegram",
        "user_id": "cli",
        "chat_id": "cli",
    }

    try:
        response = _post_json(API_URL, payload)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(response.get("reply_text", ""))
    return 0


def _post_json(url: str, payload: dict[str, str]) -> dict[str, object]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Buddy API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Buddy API at {url}: {exc.reason}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
