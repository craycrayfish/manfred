"""Tests for twitter.py"""
import argparse
import json
from unittest.mock import MagicMock, patch

import pytest
import twitter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
ALL_VARS = {
    "X_BEARER_TOKEN": "bearer",
}

ALL_POST_VARS = {
    "X_API_KEY": "api_key",
    "X_API_SECRET": "api_secret",
    "X_ACCESS_TOKEN": "access_token",
    "X_ACCESS_TOKEN_SECRET": "access_token_secret",
}


# ---------------------------------------------------------------------------
# check_credentials
# ---------------------------------------------------------------------------
class TestCheckCredentials:
    def test_all_present(self, monkeypatch):
        for k, v in ALL_VARS.items():
            monkeypatch.setenv(k, v)

        result = twitter.check_credentials(twitter.SEARCH_VARS)

        assert result == ALL_VARS

    def test_missing_bearer_token(self, monkeypatch, capsys):
        monkeypatch.delenv("X_BEARER_TOKEN", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            twitter.check_credentials(twitter.SEARCH_VARS)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert "X_BEARER_TOKEN" in err["missing"]


# ---------------------------------------------------------------------------
# cmd_search
# ---------------------------------------------------------------------------
class TestCmdSearch:
    def _set_all_env(self, monkeypatch):
        for k, v in ALL_VARS.items():
            monkeypatch.setenv(k, v)

    def test_empty_response(self, monkeypatch, capsys):
        self._set_all_env(monkeypatch)

        mock_response = MagicMock()
        mock_response.data = None
        mock_response.includes = None

        mock_client = MagicMock()
        mock_client.search_recent_tweets.return_value = mock_response

        args = argparse.Namespace(query="SNF robots", max_results=10)
        with patch.object(twitter, "get_client", return_value=mock_client):
            twitter.cmd_search(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"tweets": []}

    def test_with_data(self, monkeypatch, capsys):
        self._set_all_env(monkeypatch)

        mock_tweet = MagicMock()
        mock_tweet.id = "tweet001"
        mock_tweet.text = "Robots in nursing homes"
        mock_tweet.author_id = "author42"
        mock_tweet.created_at = None
        mock_tweet.public_metrics = {"like_count": 5, "retweet_count": 1}
        mock_tweet.entities = {"urls": [{"expanded_url": "https://example.com"}]}

        mock_user = MagicMock()
        mock_user.id = "author42"
        mock_user.username = "alice"
        mock_user.name = "Alice Smith"

        mock_response = MagicMock()
        mock_response.data = [mock_tweet]
        mock_response.includes = {"users": [mock_user]}

        mock_client = MagicMock()
        mock_client.search_recent_tweets.return_value = mock_response

        args = argparse.Namespace(query="nursing home robots", max_results=10)
        with patch.object(twitter, "get_client", return_value=mock_client):
            twitter.cmd_search(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output["tweets"]) == 1
        tweet = output["tweets"][0]
        assert tweet["id"] == "tweet001"
        assert tweet["text"] == "Robots in nursing homes"
        assert tweet["author_username"] == "alice"
        assert tweet["urls"] == ["https://example.com"]

    def test_api_error_exits(self, monkeypatch, capsys):
        self._set_all_env(monkeypatch)

        import tweepy

        mock_client = MagicMock()
        mock_client.search_recent_tweets.side_effect = tweepy.TweepyException("rate limit")

        args = argparse.Namespace(query="robots", max_results=10)
        with patch.object(twitter, "get_client", return_value=mock_client):
            with pytest.raises(SystemExit) as exc_info:
                twitter.cmd_search(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert "rate limit" in err["error"]


# ---------------------------------------------------------------------------
# cmd_post
# ---------------------------------------------------------------------------
class TestCmdPost:
    def _set_post_env(self, monkeypatch):
        for k, v in ALL_POST_VARS.items():
            monkeypatch.setenv(k, v)

    def test_post_success(self, monkeypatch, capsys):
        self._set_post_env(monkeypatch)

        mock_response = MagicMock()
        mock_response.data = {"id": "12345"}

        mock_client = MagicMock()
        mock_client.create_tweet.return_value = mock_response

        args = argparse.Namespace(text="Hello from Qrobots!")
        with patch.object(twitter, "get_post_client", return_value=mock_client):
            twitter.cmd_post(args)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == {"id": "12345", "text": "Hello from Qrobots!"}
        mock_client.create_tweet.assert_called_once_with(text="Hello from Qrobots!")

    def test_post_empty_text(self, monkeypatch, capsys):
        self._set_post_env(monkeypatch)

        args = argparse.Namespace(text="   ")
        with pytest.raises(SystemExit) as exc_info:
            twitter.cmd_post(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert err["error"] == "Tweet text cannot be empty"

    def test_post_exceeds_280_chars(self, monkeypatch, capsys):
        self._set_post_env(monkeypatch)

        args = argparse.Namespace(text="x" * 281)
        with pytest.raises(SystemExit) as exc_info:
            twitter.cmd_post(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert "280 characters" in err["error"]
        assert err["length"] == 281

    def test_post_missing_credentials(self, monkeypatch, capsys):
        for k in ALL_POST_VARS:
            monkeypatch.delenv(k, raising=False)

        args = argparse.Namespace(text="test tweet")
        with pytest.raises(SystemExit) as exc_info:
            twitter.cmd_post(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        for k in ALL_POST_VARS:
            assert k in err["missing"]

    def test_post_api_error_exits(self, monkeypatch, capsys):
        self._set_post_env(monkeypatch)

        import tweepy

        mock_client = MagicMock()
        mock_client.create_tweet.side_effect = tweepy.TweepyException("forbidden")

        args = argparse.Namespace(text="Hello!")
        with patch.object(twitter, "get_post_client", return_value=mock_client):
            with pytest.raises(SystemExit) as exc_info:
                twitter.cmd_post(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert "forbidden" in err["error"]

    def test_post_none_response_exits(self, monkeypatch, capsys):
        self._set_post_env(monkeypatch)

        mock_response = MagicMock()
        mock_response.data = None

        mock_client = MagicMock()
        mock_client.create_tweet.return_value = mock_response

        args = argparse.Namespace(text="Hello!")
        with patch.object(twitter, "get_post_client", return_value=mock_client):
            with pytest.raises(SystemExit) as exc_info:
                twitter.cmd_post(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert "No data returned" in err["error"]
