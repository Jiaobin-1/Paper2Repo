from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import json

import pytest
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.llm_client import LLMClient, _balanced_json_from, _extract_json_object, _load_json_object


class _TinySchema(BaseModel):
    name: str


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content
        self.refusal = None


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeChatResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]
        self.usage = {"total_tokens": 7}


class _FakeResponsesResponse:
    output_text = '{"name": "responses"}'
    usage = {"total_tokens": 5}


class _FakeChatCompletions:
    def __init__(self, calls: list[dict], content: str = '{"name": "chat"}') -> None:
        self.calls = calls
        self.content = content

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeChatResponse(self.content)


class _FakeResponses:
    def __init__(self, calls: list[dict], fail: bool = False) -> None:
        self.calls = calls
        self.fail = fail

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("responses unavailable")
        return _FakeResponsesResponse()


class _FakeClient:
    def __init__(self, responses_calls: list[dict], chat_calls: list[dict], *, responses_fail: bool = False) -> None:
        self.responses = _FakeResponses(responses_calls, fail=responses_fail)
        self.chat = type("Chat", (), {"completions": _FakeChatCompletions(chat_calls)})()


def _configured_client(monkeypatch, isolated_settings, base_url: str = "https://api.openai.com/v1") -> LLMClient:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", base_url)
    get_settings.cache_clear()
    return LLMClient(model_name="test-model")

# ---------------------------------------------------------------------------
# _balanced_json_from
# ---------------------------------------------------------------------------

class TestBalancedJsonFrom:
    def test_simple_object(self):
        content = '{"key": "value"}'
        result = _balanced_json_from(content, 0)
        assert result == '{"key": "value"}'

    def test_nested_object(self):
        content = '{"outer": {"inner": 42}}'
        result = _balanced_json_from(content, 0)
        assert result == '{"outer": {"inner": 42}}'

    def test_trailing_text_after_object(self):
        content = '{"key": "value"} some trailing text'
        result = _balanced_json_from(content, 0)
        assert result == '{"key": "value"}'

    def test_leading_text_before_object(self):
        content = 'Here is the JSON: {"key": "value"} done'
        start = content.index("{")
        result = _balanced_json_from(content, start)
        assert result == '{"key": "value"}'

    def test_string_with_braces_inside(self):
        content = '{"msg": "hello {world} end"}'
        result = _balanced_json_from(content, 0)
        assert result == '{"msg": "hello {world} end"}'

    def test_escaped_quote_in_string(self):
        content = r'{"msg": "he said \"hi\""}'
        result = _balanced_json_from(content, 0)
        assert result == r'{"msg": "he said \"hi\""}'

    def test_incomplete_json_returns_none(self):
        content = '{"key": "value"'
        result = _balanced_json_from(content, 0)
        assert result is None

    def test_empty_object(self):
        content = '{}'
        result = _balanced_json_from(content, 0)
        assert result == '{}'

    def test_deeply_nested(self):
        content = '{"a": {"b": {"c": {"d": 1}}}}'
        result = _balanced_json_from(content, 0)
        assert result == '{"a": {"b": {"c": {"d": 1}}}}'
        parsed = json.loads(result)
        assert parsed["a"]["b"]["c"]["d"] == 1

    def test_array_inside_object(self):
        content = '{"items": [1, 2, 3]}'
        result = _balanced_json_from(content, 0)
        assert result == '{"items": [1, 2, 3]}'

    def test_returns_from_start_not_from_brace(self):
        # _balanced_json_from returns content[start:end+1], not content[brace_pos:end+1]
        # It's always called with start at a { in practice (from _extract_json_object)
        content = 'text {"key": 1} more'
        result = _balanced_json_from(content, 0)
        # returns from start=0 to the closing }, so includes prefix
        assert result == 'text {"key": 1}'

    def test_multiple_objects_returns_first_complete(self):
        content = '{"a": 1}{"b": 2}'
        result = _balanced_json_from(content, 0)
        assert result == '{"a": 1}'


# ---------------------------------------------------------------------------
# _extract_json_object
# ---------------------------------------------------------------------------

class TestExtractJsonObject:
    def test_clean_json(self):
        result = _extract_json_object('{"key": "value"}')
        assert result == '{"key": "value"}'

    def test_json_with_prefix_text(self):
        result = _extract_json_object('Here is the output:\n{"key": "value"}\nDone.')
        assert result == '{"key": "value"}'

    def test_json_with_suffix_text(self):
        result = _extract_json_object('{"key": "value"}\nNote: this is the result.')
        assert result == '{"key": "value"}'

    def test_no_json_returns_none(self):
        result = _extract_json_object("no json here")
        assert result is None

    def test_invalid_json_object_skipped(self):
        # First { is incomplete, second is valid
        result = _extract_json_object('{incomplete {"valid": true}')
        assert result == '{"valid": true}'

    def test_code_fenced_json_not_handled_here(self):
        # _extract_json_object doesn't strip fences; _load_json_object does
        result = _extract_json_object('```json\n{"key": 1}\n```')
        # The { inside the fence should still be found
        assert result is not None


# ---------------------------------------------------------------------------
# _load_json_object
# ---------------------------------------------------------------------------

class TestLoadJsonObject:
    def test_clean_json(self):
        result = _load_json_object('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        result = _load_json_object('Here is the JSON:\n{"key": "value"}\nEnd.')
        assert result == {"key": "value"}

    def test_code_fenced_json(self):
        result = _load_json_object('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_code_fenced_without_json_label(self):
        result = _load_json_object('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_rejects_non_object(self):
        with pytest.raises(ValueError, match="JSON object"):
            _load_json_object('[1, 2, 3]')

    def test_rejects_plain_string(self):
        with pytest.raises(ValueError):
            _load_json_object('"just a string"')

    def test_rejects_garbage(self):
        with pytest.raises((json.JSONDecodeError, ValueError)):
            _load_json_object("not json at all")

    def test_llm_response_with_extra_text(self):
        content = (
            "Sure, here is the analysis:\n"
            "```json\n"
            '{"domain": "llm", "paper_type": "experimental"}\n'
            "```\n"
            "Hope this helps!"
        )
        result = _load_json_object(content)
        assert result["domain"] == "llm"
        assert result["paper_type"] == "experimental"

    def test_llm_response_with_prefix_only(self):
        content = 'The result is: {"name": "test", "score": 0.95}'
        result = _load_json_object(content)
        assert result["name"] == "test"
        assert result["score"] == 0.95

    def test_nested_json_in_noisy_text(self):
        content = (
            "I analyzed the paper.\n"
            "Some intermediate reasoning here.\n"
            '{"background": "Deep learning has...", "core_problem": "Efficiency"}\n'
            "That's my analysis."
        )
        result = _load_json_object(content)
        assert "background" in result
        assert "core_problem" in result


class TestStructuredOutputModes:
    def test_uses_responses_structured_for_official_openai(self, isolated_settings, monkeypatch):
        responses_calls: list[dict] = []
        chat_calls: list[dict] = []
        client = _configured_client(monkeypatch, isolated_settings)
        monkeypatch.setattr(client, "client", lambda: _FakeClient(responses_calls, chat_calls))

        result = client.structured_output(system_prompt="system", user_prompt="user", schema_model=_TinySchema)

        assert result.name == "responses"
        assert responses_calls[0]["store"] is False
        assert responses_calls[0]["text"]["format"]["type"] == "json_schema"
        assert chat_calls == []
        assert client.last_call_meta["mode"] == "responses_structured"

    def test_falls_back_to_chat_structured_when_responses_fails(self, isolated_settings, monkeypatch):
        responses_calls: list[dict] = []
        chat_calls: list[dict] = []
        client = _configured_client(monkeypatch, isolated_settings)
        monkeypatch.setattr(
            client,
            "client",
            lambda: _FakeClient(responses_calls, chat_calls, responses_fail=True),
        )

        result = client.structured_output(system_prompt="system", user_prompt="user", schema_model=_TinySchema)

        assert result.name == "chat"
        assert responses_calls
        assert chat_calls[0]["response_format"]["type"] == "json_schema"
        assert chat_calls[0]["store"] is False
        assert client.last_call_meta["mode"] == "chat_structured"
        assert client.last_call_meta["attempts"] == 2

    def test_non_official_base_url_uses_legacy_json_mode(self, isolated_settings, monkeypatch):
        responses_calls: list[dict] = []
        chat_calls: list[dict] = []
        client = _configured_client(monkeypatch, isolated_settings, base_url="https://example.test/v1")
        monkeypatch.setattr(client, "client", lambda: _FakeClient(responses_calls, chat_calls))

        result = client.structured_output(system_prompt="system", user_prompt="user", schema_model=_TinySchema)

        assert result.name == "chat"
        assert responses_calls == []
        assert chat_calls[0]["response_format"] == {"type": "json_object"}
        assert "store" not in chat_calls[0]
        assert client.last_call_meta["mode"] == "chat_json_legacy"
