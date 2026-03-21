# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "requests>=2.31",
#   "python-dotenv",
# ]
# ///

import json
import os
import sys

import requests
from dotenv import find_dotenv, load_dotenv

RESPONSES_URL = "https://api.x.ai/v1/responses"
MODEL = "grok-4-1-fast"

USER_PROMPT = """Search X right now and identify the top 10 trending topics in robotics, automation, and humanoid robots.

For each topic, provide:
- The topic name or hashtag
- A brief summary of what people are discussing
- 2-3 source tweets that best represent the conversation — include the tweet URL (https://x.com/<username>/status/<id>), the author's username, and the exact or near-exact tweet text
- An engagement level: high, medium, or low

Return your response as valid JSON only, with this exact structure:
{
  "trending_topics": [
    {
      "topic": "string",
      "summary": "string",
      "source_tweets": [
        {
          "url": "https://x.com/username/status/tweet_id",
          "author": "@username",
          "text": "exact or near-exact tweet text"
        }
      ],
      "engagement_level": "high|medium|low"
    }
  ]
}

Do not include any text outside the JSON object."""


def main() -> None:
    load_dotenv(find_dotenv())

    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        print(
            json.dumps({"error": "Missing required env var", "missing": ["XAI_API_KEY"]}),
            file=sys.stderr,
        )
        sys.exit(1)

    payload = {
        "model": MODEL,
        "input": [{"role": "user", "content": USER_PROMPT}],
        "tools": [{"type": "x_search"}],
    }

    resp = requests.post(
        RESPONSES_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )

    if not resp.ok:
        print(
            json.dumps({"error": f"API error {resp.status_code}", "detail": resp.text}),
            file=sys.stderr,
        )
        sys.exit(1)

    # Extract text content from the Responses API output array
    raw = ""
    for block in resp.json().get("output", []):
        if block.get("type") == "message":
            for part in block.get("content", []):
                if part.get("type") == "output_text":
                    raw = part.get("text", "").strip()
                    break

    if not raw:
        print(
            json.dumps({"error": "No text content in response", "raw": resp.json()}),
            file=sys.stderr,
        )
        sys.exit(1)

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(
            json.dumps({"error": "Failed to parse response as JSON", "detail": str(exc), "raw": raw}),
            file=sys.stderr,
        )
        sys.exit(1)

    print(json.dumps(parsed, indent=2))


if __name__ == "__main__":
    main()
