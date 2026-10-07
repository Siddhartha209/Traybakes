"""
Unit tests for research_agent/json_utils.py.

These cover the JSON extraction/repair path that used to be the sole
mechanism every node relied on (before llm_json / Groq JSON mode was
introduced), and is still the fallback if JSON mode is ever bypassed.
Run with: pytest tests/test_json_utils.py -v
"""

import json
import pytest

from research_agent.json_utils import clean_llm_text, repair_json, extract_json_object


class TestCleanLlmText:
    def test_strips_json_fence(self):
        raw = '```json\n{"a": 1}\n```'
        assert clean_llm_text(raw) == '{"a": 1}'

    def test_strips_bare_fence(self):
        raw = '```\n{"a": 1}\n```'
        assert clean_llm_text(raw) == '{"a": 1}'

    def test_no_fence_unchanged(self):
        raw = '{"a": 1}'
        assert clean_llm_text(raw) == '{"a": 1}'


class TestRepairJson:
    def test_smart_quotes(self):
        raw = '{\u201ca\u201d: 1}'
        assert repair_json(raw) == {"a": 1}

    def test_trailing_comma_object(self):
        raw = '{"a": 1, "b": 2,}'
        assert repair_json(raw) == {"a": 1, "b": 2}

    def test_trailing_comma_array(self):
        raw = '{"a": [1, 2, 3,]}'
        assert repair_json(raw) == {"a": [1, 2, 3]}

    def test_unrepairable_raises(self):
        with pytest.raises(json.JSONDecodeError):
            repair_json('{"a": }')


class TestExtractJsonObject:
    def test_clean_json_parses_directly(self):
        raw = '{"patterns": [{"name": "x"}]}'
        result = extract_json_object(raw, node_name="test")
        assert result == {"patterns": [{"name": "x"}]}

    def test_fenced_json_parses(self):
        raw = '```json\n{"gaps": []}\n```'
        result = extract_json_object(raw, node_name="test")
        assert result == {"gaps": []}

    def test_leading_trailing_prose_is_stripped_by_regex(self):
        raw = 'Sure, here is the JSON:\n{"opportunities": [1, 2, 3]}\nHope that helps!'
        result = extract_json_object(raw, node_name="test")
        assert result == {"opportunities": [1, 2, 3]}

    def test_malformed_but_repairable_json(self):
        raw = "{'patterns': [{'name': 'x', 'description': 'y',}]}"
        result = extract_json_object(raw, node_name="test")
        assert result["patterns"][0]["name"] == "x"

    def test_no_json_object_raises_value_error(self):
        with pytest.raises(ValueError):
            extract_json_object("no json here at all", node_name="test")

    def test_completely_unparseable_raises_value_error_not_json_decode_error(self):
        raw = '{"patterns": [{"name": "x" "broken"}]}'
        with pytest.raises(ValueError):
            extract_json_object(raw, node_name="test")

    def test_truncated_json_raises_value_error(self):
        raw = '{"patterns": [{"name": "Easter Promotions", "description": "Compan'
        with pytest.raises(ValueError):
            extract_json_object(raw, node_name="test")