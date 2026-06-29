#!/usr/bin/env python3
"""UserPromptSubmit hook: inject relevant long-term memory into the turn.

Flow (must stay fast and never error the turn):
  1. Read the hook stdin JSON -> `prompt`.
  2. **Gate locally** (no network, no LLM) — only proceed when the prompt looks
     memory-relevant. Most prompts gate out in microseconds and print `{}`.
  3. When gated in, run `brain recall "<prompt>" --k 5 --json` and emit
     `{"additionalSystemPrompt": "..."}` with the hits.
  4. On empty / offline / timeout / any error -> print `{}`.

Output contract: a single JSON object on stdout. `{}` means "no injection".
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import brain_cli  # noqa: E402

# ---- gate (§4.1.1) ---------------------------------------------------------

MIN_LEN = 12

# Continuation acknowledgements — never worth a recall.
ACKS = {
    "yes", "no", "ok", "okay", "yep", "yeah", "sure", "go", "go on", "continue",
    "thanks", "thank you", "thx", "done", "got it", "k", "y", "n", "stop", "wait",
    "nvm", "cool", "great", "nice", "please", "ya", "yup", "right",
}

# Signals that the user is leaning on durable memory (prefs/habits/past work).
_TRIGGER = re.compile(
    r"""
    \bremember\b | \brecall\b | \busually\b | \bprefer\w*\b | \bhabit\b |
    \bdecid\w+\b | \bdecision\b | \bconvention\w*\b | \bestablish\w+\b |
    \blast\s+time\b | \bpreviously\b |
    \bmy\s+(setup|config|preferences?|workflow|style|stack)\b |
    how\s+do\s+(i|we) | what\s+did\s+(i|we) | what'?s\s+my | whats\s+my |
    \bwe\s+(decided|established|agreed|use|prefer)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def is_memory_relevant(prompt: str) -> bool:
    p = (prompt or "").strip()
    if len(p) < MIN_LEN:
        return False
    if p.lower() in ACKS:
        return False
    if p[0] in "/!":  # slash command or shell echo
        return False
    return bool(_TRIGGER.search(p))


# ---- recall + injection ----------------------------------------------------


def recall(query: str) -> list[dict]:
    """Call the bundled CLI; return hits (empty on offline/timeout)."""
    cmd = [sys.executable, str(brain_cli()), "recall", query, "--k", "5", "--json"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
    if out.returncode != 0 or not out.stdout.strip():
        return []
    return json.loads(out.stdout).get("hits", [])


def build_injection(hits: list[dict]) -> dict:
    if not hits:
        return {}
    lines, ids = [], []
    for h in hits:
        snippet = (h.get("snippet") or "").strip()
        line = f"- [{h.get('type', '?')}] {h.get('title', '')}"
        if snippet:
            line += f": {snippet}"
        lines.append(line)
        if h.get("id"):
            ids.append(h["id"])
    text = (
        "Relevant long-term memory (from brain):\n"
        + "\n".join(lines)
        + f"\n(ids: {', '.join(ids)})"
    )
    return {"additionalSystemPrompt": text}


def main(stdin_text: str | None = None) -> None:
    raw = stdin_text if stdin_text is not None else sys.stdin.read()
    try:
        prompt = json.loads(raw).get("prompt", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        print("{}")
        return
    if not is_memory_relevant(prompt):
        print("{}")
        return
    try:
        hits = recall(prompt)
    except Exception:  # offline, timeout, bad JSON — recall is best-effort
        print("{}")
        return
    print(json.dumps(build_injection(hits)))


if __name__ == "__main__":
    main()
