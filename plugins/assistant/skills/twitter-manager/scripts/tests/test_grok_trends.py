"""Tests for grok_trends.py"""
import json
from unittest.mock import patch

import pytest
import grok_trends

VALID_PAYLOAD = {
    "trending_topics": [
        {
            "topic": "#HumanoidRobots",
            "summary": "Discussion about humanoid robot deployments",
            "example_tweets": ["Tweet one", "Tweet two"],
            "engagement_level": "high",
        }
    ]
}


def _make_responses_api_response(text: str) -> dict:
    """Build a fake xAI Responses API response dict."""
    return {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": text}],
            }
        ]
    }


class TestGrokTrends:
    def test_missing_api_key(self, monkeypatch, capsys):
        monkeypatch.delenv("XAI_API_KEY", raising=False)

        with patch("grok_trends.load_dotenv"), pytest.raises(SystemExit) as exc_info:
            grok_trends.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert "missing" in err
        assert "XAI_API_KEY" in err["missing"]

    def test_valid_response(self, monkeypatch, capsys):
        monkeypatch.setenv("XAI_API_KEY", "fake-key")

        mock_resp = type("R", (), {
            "ok": True,
            "json": lambda self: _make_responses_api_response(json.dumps(VALID_PAYLOAD)),
        })()

        with patch("grok_trends.requests.post", return_value=mock_resp):
            grok_trends.main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "trending_topics" in output
        assert len(output["trending_topics"]) == 1
        assert output["trending_topics"][0]["topic"] == "#HumanoidRobots"

    def test_invalid_json_response(self, monkeypatch, capsys):
        monkeypatch.setenv("XAI_API_KEY", "fake-key")

        mock_resp = type("R", (), {
            "ok": True,
            "json": lambda self: _make_responses_api_response("this is not json at all"),
        })()

        with patch("grok_trends.requests.post", return_value=mock_resp):
            with pytest.raises(SystemExit) as exc_info:
                grok_trends.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert "error" in err
        assert "parse" in err["error"].lower()

    def test_api_error_response(self, monkeypatch, capsys):
        monkeypatch.setenv("XAI_API_KEY", "fake-key")

        mock_resp = type("R", (), {
            "ok": False,
            "status_code": 403,
            "text": "Forbidden",
        })()

        with patch("grok_trends.requests.post", return_value=mock_resp):
            with pytest.raises(SystemExit) as exc_info:
                grok_trends.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert "403" in err["error"]

    def test_markdown_fenced_json(self, monkeypatch, capsys):
        monkeypatch.setenv("XAI_API_KEY", "fake-key")

        fenced = f"```json\n{json.dumps(VALID_PAYLOAD)}\n```"
        mock_resp = type("R", (), {
            "ok": True,
            "json": lambda self: _make_responses_api_response(fenced),
        })()

        with patch("grok_trends.requests.post", return_value=mock_resp):
            grok_trends.main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "trending_topics" in output
