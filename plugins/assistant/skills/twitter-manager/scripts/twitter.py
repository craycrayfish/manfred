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

from dotenv import load_dotenv
import tweepy

load_dotenv()

REQUIRED_VARS = [
    "TWITTER_BEARER_TOKEN",
    "TWITTER_USER_ID",
    "TWITTER_API_KEY",
    "TWITTER_API_SECRET",
    "TWITTER_ACCESS_TOKEN",
    "TWITTER_ACCESS_TOKEN_SECRET",
]


def check_credentials() -> dict[str, str]:
    missing = [v for v in REQUIRED_VARS if not os.environ.get(v)]
    if missing:
        print(
            json.dumps({"error": "Missing required env vars", "missing": missing}),
            file=sys.stderr,
        )
        sys.exit(1)
    return {v: os.environ[v] for v in REQUIRED_VARS}


def get_client(creds: dict[str, str]) -> tweepy.Client:
    return tweepy.Client(
        bearer_token=creds["TWITTER_BEARER_TOKEN"],
        consumer_key=creds["TWITTER_API_KEY"],
        consumer_secret=creds["TWITTER_API_SECRET"],
        access_token=creds["TWITTER_ACCESS_TOKEN"],
        access_token_secret=creds["TWITTER_ACCESS_TOKEN_SECRET"],
        wait_on_rate_limit=True,
    )


def cmd_mentions(args: argparse.Namespace) -> None:
    creds = check_credentials()
    client = get_client(creds)
    user_id = creds["TWITTER_USER_ID"]

    response = client.get_users_mentions(
        id=user_id,
        max_results=args.max_results,
        tweet_fields=[
            "id",
            "text",
            "author_id",
            "created_at",
            "conversation_id",
            "in_reply_to_user_id",
            "referenced_tweets",
        ],
        expansions=["author_id", "referenced_tweets.id"],
        user_fields=["username", "name"],
    )

    users_by_id: dict[str, dict] = {}
    if response.includes and "users" in response.includes:
        for user in response.includes["users"]:
            users_by_id[user.id] = {"username": user.username, "name": user.name}

    ref_tweets_by_id: dict[str, str] = {}
    if response.includes and "tweets" in response.includes:
        for tweet in response.includes["tweets"]:
            ref_tweets_by_id[tweet.id] = tweet.text

    mentions = []
    if response.data:
        for tweet in response.data:
            author_info = users_by_id.get(tweet.author_id, {})
            referenced = []
            if tweet.referenced_tweets:
                for ref in tweet.referenced_tweets:
                    referenced.append(
                        {
                            "type": ref.type,
                            "id": ref.id,
                            "text": ref_tweets_by_id.get(ref.id, ""),
                        }
                    )
            mentions.append(
                {
                    "id": tweet.id,
                    "text": tweet.text,
                    "author_username": author_info.get("username", ""),
                    "author_name": author_info.get("name", ""),
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    "conversation_id": tweet.conversation_id,
                    "in_reply_to_user_id": tweet.in_reply_to_user_id,
                    "referenced_tweets": referenced,
                }
            )

    print(json.dumps({"mentions": mentions}, indent=2))


def cmd_reply(args: argparse.Namespace) -> None:
    creds = check_credentials()
    client = get_client(creds)

    response = client.create_tweet(
        text=args.text,
        in_reply_to_tweet_id=args.tweet_id,
    )

    tweet = response.data
    print(json.dumps({"id": tweet["id"], "text": tweet["text"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Twitter API v2 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mentions_parser = subparsers.add_parser("mentions", help="Fetch recent mentions")
    mentions_parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        dest="max_results",
        help="Maximum number of results to return (5-100)",
    )

    reply_parser = subparsers.add_parser("reply", help="Post a reply to a tweet")
    reply_parser.add_argument("--tweet-id", required=True, dest="tweet_id", help="ID of the tweet to reply to")
    reply_parser.add_argument("--text", required=True, help="Text of the reply")

    args = parser.parse_args()

    if args.command == "mentions":
        cmd_mentions(args)
    elif args.command == "reply":
        cmd_reply(args)


if __name__ == "__main__":
    main()
