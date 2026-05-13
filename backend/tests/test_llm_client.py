from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import json

import pytest

from app.services.llm_client import _balanced_json_from, _extract_json_object, _load_json_object

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
