"""Tests for the two-step vLLM endpoint validation helper.

The previous single-shot validator only inspected status codes, so a server
that didn't enforce auth on /v1/models accepted any key. ``_validate_vllm_endpoint``
now probes without auth first, then verifies the user's key only when the
server actually requires one.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from lfx.base.models.unified_models.credentials import _validate_vllm_endpoint


def _resp(status: int) -> SimpleNamespace:
    """Minimal stand-in for ``requests.Response``."""

    def _raise() -> None:
        if status >= 400:
            import requests

            err = requests.HTTPError(f"HTTP {status}")
            raise err

    return SimpleNamespace(status_code=status, raise_for_status=_raise)


class TestServerEnforcesAuth:
    """Step 1 returns 401/403 → server requires a key. Step 2 must succeed."""

    def test_no_key_when_server_requires_auth_raises(self) -> None:
        with patch("requests.get", side_effect=[_resp(401)]):
            with pytest.raises(ValueError, match="requires an API key"):
                _validate_vllm_endpoint(
                    "https://vllm.example.com/v1",
                    None,
                    provider_label="vLLM Language",
                    key_var_name="VLLM_API_KEY",
                )

    def test_wrong_key_is_rejected(self) -> None:
        # Step 1 (no auth): 401 — server enforces auth.
        # Step 2 (with key): 401 — key is wrong.
        with patch("requests.get", side_effect=[_resp(401), _resp(401)]):
            with pytest.raises(ValueError, match="was rejected"):
                _validate_vllm_endpoint(
                    "https://vllm.example.com/v1",
                    "wrong-key",
                    provider_label="vLLM Language",
                    key_var_name="VLLM_API_KEY",
                )

    def test_correct_key_passes(self) -> None:
        # Step 1: 401 — server enforces. Step 2: 200 — key is correct.
        with patch("requests.get", side_effect=[_resp(403), _resp(200)]) as mget:
            _validate_vllm_endpoint(
                "https://vllm.example.com/v1",
                "correct-key",
                provider_label="vLLM Language",
                key_var_name="VLLM_API_KEY",
            )
        # Step 2 must carry the Authorization header — that's the whole point.
        assert mget.call_args_list[1].kwargs["headers"]["Authorization"] == "Bearer correct-key"

    def test_403_treated_same_as_401(self) -> None:
        # Some servers signal "auth required" with 403 instead of 401.
        with patch("requests.get", side_effect=[_resp(403), _resp(403)]):
            with pytest.raises(ValueError, match="was rejected"):
                _validate_vllm_endpoint(
                    "https://vllm.example.com/v1",
                    "k",
                    provider_label="vLLM Language",
                    key_var_name="VLLM_API_KEY",
                )


class TestServerDoesNotEnforceAuth:
    """Step 1 returns 200 → server is open. We can't validate the key here."""

    def test_open_server_accepts_with_key(self) -> None:
        # A perfectly fine config (operator left /v1/models open). Validation
        # must accept and only log; it MUST NOT mistakenly reject the key.
        with patch("requests.get", side_effect=[_resp(200)]) as mget:
            _validate_vllm_endpoint(
                "https://vllm.example.com/v1",
                "any-key",
                provider_label="vLLM Language",
                key_var_name="VLLM_API_KEY",
            )
        # Only one call — no need to re-probe with auth when server is open.
        assert mget.call_count == 1

    def test_open_server_accepts_without_key(self) -> None:
        with patch("requests.get", side_effect=[_resp(200)]):
            _validate_vllm_endpoint(
                "https://vllm.example.com/v1",
                None,
                provider_label="vLLM Language",
                key_var_name="VLLM_API_KEY",
            )


class TestNetworkErrors:
    def test_connection_error_becomes_value_error(self) -> None:
        import requests

        with patch("requests.get", side_effect=requests.ConnectionError("nope")):
            with pytest.raises(ValueError, match="Could not connect"):
                _validate_vllm_endpoint(
                    "https://vllm.example.com/v1",
                    "k",
                    provider_label="vLLM Language",
                    key_var_name="VLLM_API_KEY",
                )

    def test_timeout_becomes_value_error(self) -> None:
        import requests

        with patch("requests.get", side_effect=requests.Timeout("slow")):
            with pytest.raises(ValueError, match="timed out"):
                _validate_vllm_endpoint(
                    "https://vllm.example.com/v1",
                    "k",
                    provider_label="vLLM Language",
                    key_var_name="VLLM_API_KEY",
                )

    def test_empty_base_url_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid vLLM Language API base URL"):
            _validate_vllm_endpoint(
                "",
                "k",
                provider_label="vLLM Language",
                key_var_name="VLLM_API_KEY",
            )


class TestUrlAssembly:
    def test_appends_v1_models_when_missing(self) -> None:
        with patch("requests.get", side_effect=[_resp(200)]) as mget:
            _validate_vllm_endpoint(
                "https://vllm.example.com",
                None,
                provider_label="vLLM Language",
                key_var_name="VLLM_API_KEY",
            )
        assert mget.call_args.args[0] == "https://vllm.example.com/v1/models"

    def test_appends_only_models_when_v1_suffix_present(self) -> None:
        with patch("requests.get", side_effect=[_resp(200)]) as mget:
            _validate_vllm_endpoint(
                "https://vllm.example.com/v1",
                None,
                provider_label="vLLM Language",
                key_var_name="VLLM_API_KEY",
            )
        assert mget.call_args.args[0] == "https://vllm.example.com/v1/models"

    def test_trailing_slash_stripped(self) -> None:
        with patch("requests.get", side_effect=[_resp(200)]) as mget:
            _validate_vllm_endpoint(
                "https://vllm.example.com/v1/",
                None,
                provider_label="vLLM Language",
                key_var_name="VLLM_API_KEY",
            )
        assert mget.call_args.args[0] == "https://vllm.example.com/v1/models"
