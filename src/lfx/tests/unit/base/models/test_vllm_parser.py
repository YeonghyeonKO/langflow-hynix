"""Tests for _parse_vllm_model_list — the permissive vLLM /v1/models parser.

The parser must handle every shape we've seen from real vLLM forks and
OpenAI-compatible proxies in front of vLLM (Qwen, MLflow gateway, etc.).
"""

from __future__ import annotations

from lfx.base.models.model_utils import _parse_vllm_model_list


class TestOpenAICompatibleShape:
    """The default OpenAI-compatible vLLM shape."""

    def test_data_with_id_objects(self) -> None:
        payload = {
            "object": "list",
            "data": [
                {"id": "Qwen3.6-35B", "object": "model", "created": 1782169781},
                {"id": "Qwen3.6-7B", "object": "model", "created": 1782169782},
            ],
        }
        assert _parse_vllm_model_list(payload) == ["Qwen3.6-35B", "Qwen3.6-7B"]

    def test_data_payload_only(self) -> None:
        # Older vLLM builds drop the top-level "object" key.
        assert _parse_vllm_model_list({"data": [{"id": "m1"}]}) == ["m1"]


class TestAlternateSchemas:
    """Permissive support for fork/proxy quirks."""

    def test_models_key_instead_of_data(self) -> None:
        # Some internal vLLM proxies rewrap as {"models": [...]}.
        assert _parse_vllm_model_list({"models": [{"id": "m1"}]}) == ["m1"]

    def test_top_level_array_of_objects(self) -> None:
        assert _parse_vllm_model_list([{"id": "a"}, {"id": "b"}]) == ["a", "b"]

    def test_top_level_array_of_strings(self) -> None:
        # A minimal gateway might just return the names.
        assert _parse_vllm_model_list(["a", "b"]) == ["a", "b"]

    def test_id_falls_back_to_name_then_model(self) -> None:
        # The spec is loose: some entries carry the name under "name" or "model".
        payload = {"data": [{"name": "alpha"}, {"model": "beta"}, {"id": "gamma"}]}
        assert _parse_vllm_model_list(payload) == ["alpha", "beta", "gamma"]


class TestDefensiveBehavior:
    def test_dedupes_and_sorts(self) -> None:
        # Duplicate-resilient because internal proxies sometimes paginate and
        # the consumer should not surface the same model twice.
        payload = {"data": [{"id": "b"}, {"id": "a"}, {"id": "b"}]}
        assert _parse_vllm_model_list(payload) == ["a", "b"]

    def test_empty_data(self) -> None:
        assert _parse_vllm_model_list({"data": []}) == []

    def test_no_recognized_keys(self) -> None:
        assert _parse_vllm_model_list({"foo": "bar"}) == []

    def test_none(self) -> None:
        assert _parse_vllm_model_list(None) == []

    def test_string_payload(self) -> None:
        # Defensive: a misconfigured server can return raw JSON-encoded text;
        # rather than crash the picker, return empty so the caller logs the
        # raw payload via its warning branch.
        assert _parse_vllm_model_list("just a string") == []

    def test_strips_whitespace_in_id(self) -> None:
        assert _parse_vllm_model_list({"data": [{"id": "  m1  "}]}) == ["m1"]

    def test_drops_entries_with_empty_id(self) -> None:
        payload = {"data": [{"id": ""}, {"id": None}, {}, {"id": "ok"}]}
        assert _parse_vllm_model_list(payload) == ["ok"]
