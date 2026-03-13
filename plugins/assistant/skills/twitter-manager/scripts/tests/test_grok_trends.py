"""Tests for grok_trends.py"""
import json
import sys
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = str(
    __import__("pathlib").Path(__file__).parent.parent.resolve()
)


def _import_grok_trends():
    """Import grok_trends module with sys.path set correctly."""
    if SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, SCRIPTS_DIR)
    import importlib
    import grok_trends  # noqa: PLC0415

    return importlib.reload(grok_trends)


VALID_RESPONSE_JSON = json.dumps(
    {
        "trending_topics": [
            {
                "topic": "#HumanoidRobots",
                "summary": "Discussion about humanoid robot deployments",
                "example_tweets": ["Tweet one", "Tweet two"],
                "engagement_level": "high",
            }
        ]
    }
)


def _make_openai_response(content: str):
    """Build a fake openai ChatCompletion response object."""
    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


class TestGrokTrends:
    def test_missing_api_key(self, monkeypatch, capsys):
        monkeypatch.delenv("XAI_API_KEY", raising=False)
        grok = _import_grok_trends()

        with pytest.raises(SystemExit) as exc_info:
            grok.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert "missing" in err
        assert "XAI_API_KEY" in err["missing"]

    def test_valid_response(self, monkeypatch, capsys):
        monkeypatch.setenv("XAI_API_KEY", "fake-key")
        grok = _import_grok_trends()

        mock_openai_instance = MagicMock()
        mock_openai_instance.chat.completions.create.return_value = (
            _make_openai_response(VALID_RESPONSE_JSON)
        )

        with patch("grok_trends.OpenAI", return_value=mock_openai_instance):
            grok.main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "trending_topics" in output
        assert isinstance(output["trending_topics"], list)
        assert len(output["trending_topics"]) == 1
        assert output["trending_topics"][0]["topic"] == "#HumanoidRobots"

    def test_invalid_json_response(self, monkeypatch, capsys):
        monkeypatch.setenv("XAI_API_KEY", "fake-key")
        grok = _import_grok_trends()

        mock_openai_instance = MagicMock()
        mock_openai_instance.chat.completions.create.return_value = (
            _make_openai_response("this is not json at all")
        )

        with patch("grok_trends.OpenAI", return_value=mock_openai_instance):
            with pytest.raises(SystemExit) as exc_info:
                grok.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        err = json.loads(captured.err)
        assert "error" in err
        assert "parse" in err["error"].lower()
