# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "tweepy>=4.14",
#   "python-dotenv",
# ]
# ///

import argparse
import json
import os
import sys

import tweepy
from dotenv import find_dotenv, load_dotenv

SEARCH_VARS = ["X_BEARER_TOKEN"]
POST_VARS = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]


def check_credentials(required: list[str]) -> dict[str, str]:
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(
            json.dumps({"error": "Missing required env vars", "missing": missing}),
            file=sys.stderr,
        )
        sys.exit(1)
    return {v: os.environ[v] for v in required}


def get_client(creds: dict[str, str]) -> tweepy.Client:
    return tweepy.Client(bearer_token=creds["X_BEARER_TOKEN"], wait_on_rate_limit=True)


def get_post_client(creds: dict[str, str]) -> tweepy.Client:
    return tweepy.Client(
        consumer_key=creds["X_API_KEY"],
        consumer_secret=creds["X_API_SECRET"],
        access_token=creds["X_ACCESS_TOKEN"],
        access_token_secret=creds["X_ACCESS_TOKEN_SECRET"],
        wait_on_rate_limit=True,
    )


def cmd_search(args: argparse.Namespace) -> None:
    creds = check_credentials(SEARCH_VARS)
    client = get_client(creds)

    try:
        response = client.search_recent_tweets(
            query=args.query,
            max_results=args.max_results,
            tweet_fields=["id", "text", "author_id", "created_at", "public_metrics", "entities"],
            expansions=["author_id"],
            user_fields=["username", "name"],
        )
    except tweepy.TweepyException as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)

    users_by_id: dict[str, dict[str, str]] = {}
    if response.includes and "users" in response.includes:
        for user in response.includes["users"]:
            users_by_id[user.id] = {"username": user.username, "name": user.name}

    tweets = []
    if response.data:
        for tweet in response.data:
            author_info = users_by_id.get(tweet.author_id, {})
            tweets.append(
                {
                    "id": tweet.id,
                    "text": tweet.text,
                    "author_username": author_info.get("username", ""),
                    "author_name": author_info.get("name", ""),
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    "metrics": tweet.public_metrics,
                    "urls": [
                        u.get("expanded_url")
                        for u in (tweet.entities or {}).get("urls", [])
                        if u.get("expanded_url")
                    ],
                }
            )

    print(json.dumps({"tweets": tweets}, indent=2))


def cmd_post(args: argparse.Namespace) -> None:
    creds = check_credentials(POST_VARS)
    client = get_post_client(creds)
    text = args.text.strip()
    if not text:
        print(json.dumps({"error": "Tweet text cannot be empty"}), file=sys.stderr)
        sys.exit(1)
    if len(text) > 280:
        print(
            json.dumps({"error": "Tweet exceeds 280 characters", "length": len(text)}),
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        response = client.create_tweet(text=text)
    except tweepy.TweepyException as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)
    if not response.data:
        print(json.dumps({"error": "No data returned from API"}), file=sys.stderr)
        sys.exit(1)
    tweet_id = response.data["id"]
    print(json.dumps({"id": tweet_id, "text": text}))


def _max_results_type(value: str) -> int:
    n = int(value)
    if not 10 <= n <= 100:
        raise argparse.ArgumentTypeError("--max-results must be between 10 and 100")
    return n


def main() -> None:
    load_dotenv(find_dotenv())

    parser = argparse.ArgumentParser(description="X API v2 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Search recent tweets")
    search_parser.add_argument("query", help="Search query (supports X query syntax)")
    search_parser.add_argument(
        "--max-results",
        type=_max_results_type,
        default=10,
        dest="max_results",
        help="Maximum number of results to return (10-100)",
    )

    post_parser = subparsers.add_parser("post", help="Post a new tweet")
    post_parser.add_argument("--text", required=True, help="Tweet text (max 280 chars)")

    args = parser.parse_args()

    if args.command == "search":
        cmd_search(args)
    elif args.command == "post":
        cmd_post(args)


if __name__ == "__main__":
    main()
