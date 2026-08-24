#!/usr/bin/env python3
"""SessionEnd hook: distill the session into durable memory and store it.

Flow (async; must never raise — a teardown error is invisible but pointless):
  1. Read hook stdin -> `transcript_path`, `session_id`.
  2. **Gate** on whether the session was meaningful (enough back-and-forth) —
     skip trivial sessions before paying for the extractor.
  3. Run a single headless `claude -p` (Sonnet) over the transcript with a
     strict JSON-schema prompt that returns only durable, reusable facts.
  4. Dedupe by normalized title and `brain write` each candidate to the inbox.

The weekly review (Phase 3) is the human filter that elevates inbox -> longterm,
so capture stays conservative but doesn't have to be perfect.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import brain_cli  # noqa: E402

# ---- session gate ----------------------------------------------------------

MIN_USER_TURNS = 2
MIN_USER_CHARS = 400
MAX_PROMPT_CHARS = 60_000  # cap transcript fed to the extractor (most recent tail)


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            b["text"] for b in content
            if isinstance(b, dict) and isinstance(b.get("text"), str)
        )
    return ""


def _role_and_text(rec: dict) -> tuple[str, str]:
    msg = rec.get("message", rec) if isinstance(rec, dict) else {}
    role = msg.get("role") or rec.get("type") or ""
    return role, _text_of(msg.get("content", ""))


def is_meaningful_session(records: list[dict]) -> bool:
    turns = 0
    chars = 0
    for rec in records:
        role, text = _role_and_text(rec)
        if role == "user":
            turns += 1
            chars += len(text)
    return turns >= MIN_USER_TURNS and chars >= MIN_USER_CHARS


# ---- transcript loading ----------------------------------------------------


def load_transcript(path: str) -> list[dict]:
    records: list[dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def transcript_to_text(records: list[dict]) -> str:
    lines = []
    for rec in records:
        role, text = _role_and_text(rec)
        if role in ("user", "assistant") and text.strip():
            lines.append(f"{role}: {text.strip()}")
    blob = "\n\n".join(lines)
    return blob[-MAX_PROMPT_CHARS:]  # keep the most recent tail under cap


# ---- extractor -------------------------------------------------------------

EXTRACTION_PROMPT = """\
You are a memory extractor for a personal assistant. Read the session transcript \
(provided on stdin) and extract ONLY durable, reusable facts worth remembering \
across future sessions: stable user preferences, working habits, decisions with \
lasting rationale, and research conclusions.

STRICT RULES:
- Output a JSON array ONLY. No prose, no markdown fences.
- Each item: {"title": str (<80 chars), "type": one of \
preference|habit|research|decision|fact|person|project|reference, \
"body": str (1-3 sentences, self-contained), "tags": [str], \
"confidence": float 0-1, "links": [str] (optional related slugs)}.
- EXCLUDE anything transient or session-specific: the current task, file paths \
touched this session, ephemeral debugging, one-off commands.
- If nothing is worth keeping, output exactly [].
- Prefer fewer, higher-quality items. Be conservative."""


def parse_extractor_output(raw: str) -> list[dict]:
    """Parse `claude -p --output-format json` stdout into a candidate list."""
    try:
        outer = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    text = outer.get("result", "") if isinstance(outer, dict) else outer
    if isinstance(text, list):
        return [c for c in text if isinstance(c, dict)]
    if not isinstance(text, str):
        return []
    text = _strip_fence(text.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    return [c for c in data if isinstance(c, dict)] if isinstance(data, list) else []


def _strip_fence(s: str) -> str:
    if s.startswith("```"):
        s = s[3:]
        if s[:4].lower() == "json":
            s = s[4:]
        if "```" in s:
            s = s[: s.rindex("```")]
    return s.strip()


def run_extractor(transcript_text: str) -> list[dict]:
    model = os.environ.get("BRAIN_EXTRACTOR_MODEL", "claude-sonnet-4-6")
    cmd = ["claude", "-p", "--model", model,
           "--output-format", "json", EXTRACTION_PROMPT]
    out = subprocess.run(cmd, input=transcript_text, capture_output=True,
                         text=True, timeout=120)
    if out.returncode != 0 or not out.stdout.strip():
        return []
    return parse_extractor_output(out.stdout)


# ---- candidate handling ----------------------------------------------------


def dedupe_candidates(cands: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for c in cands:
        key = " ".join((c.get("title") or "").lower().split())
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def brain_write_cmd(candidate: dict, session_id: str) -> list[str]:
    cmd = [
        sys.executable, str(brain_cli()), "write",
        "--title", candidate.get("title", ""),
        "--type", candidate.get("type", "fact"),
        "--tier", "inbox",
        "--body-file", "-",
    ]
    if candidate.get("confidence") is not None:
        cmd += ["--confidence", str(candidate["confidence"])]
    if candidate.get("tags"):
        cmd += ["--tags", ",".join(candidate["tags"])]
    if candidate.get("links"):
        cmd += ["--links", ",".join(candidate["links"])]
    if session_id:
        cmd += ["--source-session", session_id]
    return cmd


def write_candidate(candidate: dict, session_id: str) -> None:
    subprocess.run(
        brain_write_cmd(candidate, session_id),
        input=candidate.get("body", ""),
        capture_output=True, text=True, timeout=10,
    )


def main(stdin_text: str | None = None) -> None:
    raw = stdin_text if stdin_text is not None else sys.stdin.read()
    try:
        data = json.loads(raw)
        tpath = data.get("transcript_path")
        sid = data.get("session_id", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return
    if not tpath:
        return
    try:
        records = load_transcript(tpath)
    except OSError:
        return
    if not is_meaningful_session(records):
        return
    try:
        candidates = dedupe_candidates(run_extractor(transcript_to_text(records)))
    except Exception:  # extractor missing/timeout/bad output — give up quietly
        return
    for c in candidates:
        try:
            write_candidate(c, sid)
        except Exception:
            continue


if __name__ == "__main__":
    main()
