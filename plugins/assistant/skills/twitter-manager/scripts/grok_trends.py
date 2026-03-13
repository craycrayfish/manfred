# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "openai>=1.0",
#   "python-dotenv",
# ]
# ///

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = (
    "You are a social media analyst specializing in robotics and automation. "
    "You have real-time access to X/Twitter and can identify what is trending right now."
)

USER_PROMPT = """Search X/Twitter right now and identify the top 10 trending topics in robotics, automation, and humanoid robots.

For each topic, provide:
- The topic name or hashtag
- A brief summary of what people are discussing
- 2-3 example tweets or paraphrased posts illustrating the conversation
- An engagement level: high, medium, or low

Return your response as valid JSON only, with this exact structure:
{
  "trending_topics": [
    {
      "topic": "string",
      "summary": "string",
      "example_tweets": ["string", "string"],
      "engagement_level": "high|medium|low"
    }
  ]
}

Do not include any text outside the JSON object."""


def main() -> None:
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        print(
            json.dumps({"error": "Missing required env var", "missing": ["XAI_API_KEY"]}),
            file=sys.stderr,
        )
        sys.exit(1)

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
    )

    response = client.chat.completions.create(
        model="grok-2-latest",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(
            json.dumps({"error": "Failed to parse Grok response as JSON", "detail": str(exc), "raw": raw}),
            file=sys.stderr,
        )
        sys.exit(1)

    print(json.dumps(parsed, indent=2))


if __name__ == "__main__":
    main()
