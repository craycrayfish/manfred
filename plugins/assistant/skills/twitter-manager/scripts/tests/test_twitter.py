"""Tests for twitter.py"""
import argparse
import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers to import the script without triggering load_dotenv side-effects
# ---------------------------------------------------------------------------
SCRIPTS_DIR = str(
    __import__("pathlib").Path(__file__).parent.parent.resolve()
)


def _import_twitter():
    """Import twitter module with sys.path set correctly."""
    if SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, SCRIPTS_DIR)
    import importlib
    import twitter  # noqa: PLC0415

    return importlib.reload(twitter)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
ALL_VARS = {
    "TWITTER_BEARER_TOKEN": "bearer",
    "TWITTER_USER_ID": "uid123",
    "TWITTER_API_KEY": "apikey",
    "TWITTER_API_SECRET": "apisecret",
    "TWITTER_ACCESS_TOKEN": "accesstoken",
    "TWITTER_ACCESS_TOKEN_SECRET": "accesssecret",
}


# ---------------------------------------------------------------------------
# check_credentials
# ---------------------------------------------------------------------------
class TestCheckCredentials:
    def test_all_present(self, monkeypatch):
        for k, v in ALL_VARS.items():
            monkeypatch.setenv(k, v)

        twitter = _import_twitter()
        result = twitter.check_credentials()

        assert result == ALL_VARS

    def test_missing_one(self, monkeypatch, capsys):
        for k, v in ALL_VARS.items():
            monkeypatch.setenv(k, v)
        monkeypatch.delenv("TWITTER_API_KEY")

        twitter = _import_twitter()
        with pytest.raises(SystemExit) as exc_info:
            twitter.check_credentials()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert "TWITTER_API_KEY" in err["missing"]

    def test_missing_all(self, monkeypatch, capsys):
        for k in ALL_VARS:
            monkeypatch.delenv(k, raising=False)

        twitter = _import_twitter()
        with pytest.raises(SystemExit) as exc_info:
            twitter.check_credentials()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert len(err["missing"]) == 6
        for var in ALL_VARS:
            assert var in err["missing"]


# ---------------------------------------------------------------------------
# cmd_mentions
# ---------------------------------------------------------------------------
class TestCmdMentions:
    def _make_args(self, max_results=10):
        args = argparse.Namespace(max_results=max_results)
        return args

    def _set_all_env(self, monkeypatch):
        for k, v in ALL_VARS.items():
            monkeypatch.setenv(k, v)

    def test_empty_response(self, monkeypatch, capsys):
        self._set_all_env(monkeypatch)
        twitter = _import_twitter()

        mock_response = MagicMock()
        mock_response.data = None
        mock_response.includes = None

        mock_client = MagicMock()
        mock_client.get_users_mentions.return_value = mock_response

        with patch.object(twitter, "get_client", return_value=mock_client):
            twitter.cmd_mentions(self._make_args())

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"mentions": []}

    def test_with_data(self, monkeypatch, capsys):
        self._set_all_env(monkeypatch)
        twitter = _import_twitter()

        # Build a fake tweet object
        mock_tweet = MagicMock()
        mock_tweet.id = "tweet001"
        mock_tweet.text = "Hello @bot"
        mock_tweet.author_id = "author42"
        mock_tweet.created_at = None
        mock_tweet.conversation_id = "conv001"
        mock_tweet.in_reply_to_user_id = None
        mock_tweet.referenced_tweets = None

        # Build a fake user expansion
        mock_user = MagicMock()
        mock_user.id = "author42"
        mock_user.username = "alice"
        mock_user.name = "Alice Smith"

        mock_response = MagicMock()
        mock_response.data = [mock_tweet]
        mock_response.includes = {"users": [mock_user]}

        mock_client = MagicMock()
        mock_client.get_users_mentions.return_value = mock_response

        with patch.object(twitter, "get_client", return_value=mock_client):
            twitter.cmd_mentions(self._make_args())

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output["mentions"]) == 1
        mention = output["mentions"][0]
        assert mention["id"] == "tweet001"
        assert mention["text"] == "Hello @bot"
        assert mention["author_username"] == "alice"


# ---------------------------------------------------------------------------
# cmd_reply
# ---------------------------------------------------------------------------
class TestCmdReply:
    def _set_all_env(self, monkeypatch):
        for k, v in ALL_VARS.items():
            monkeypatch.setenv(k, v)

    def test_reply_success(self, monkeypatch, capsys):
        self._set_all_env(monkeypatch)
        twitter = _import_twitter()

        mock_response = MagicMock()
        mock_response.data = {"id": "123", "text": "hello"}

        mock_client = MagicMock()
        mock_client.create_tweet.return_value = mock_response

        args = argparse.Namespace(tweet_id="orig_tweet", text="hello")

        with patch.object(twitter, "get_client", return_value=mock_client):
            twitter.cmd_reply(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["id"] == "123"
        assert output["text"] == "hello"
