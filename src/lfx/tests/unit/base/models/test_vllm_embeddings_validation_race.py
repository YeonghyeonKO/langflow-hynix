"""Issue #34 — vLLM Embeddings credential validation must not 401 during the save race.

The provider modal saves VLLM_EMBEDDINGS_API_BASE and VLLM_EMBEDDINGS_API_KEY concurrently.
The base-URL save (the provider's primary variable, so the one that triggers backend
validation) re-reads the key from the DB, which may not be committed yet. Without a guard,
``validate_model_provider_key`` fires an unauthenticated probe, the server returns 401/403,
and the first attempt fails with a spurious "Authentication failed" — even though the key is
correct. The retry succeeds because the key is committed by then.

These tests pin the fixed behavior:

- No key yet  -> validation is skipped (no HTTP call, no raise).
- Key present -> the endpoint is probed with the bearer token; a real 401 still raises.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from lfx.base.models.unified_models.credentials import validate_model_provider_key

BASE = "http://common.llm.skhynix.com"


def test_skips_probe_when_key_not_yet_available():
    """No VLLM_EMBEDDINGS_API_KEY -> skip the API call entirely (avoids the save-race 401)."""
    with patch("requests.get") as mock_get:
        # Must not raise, and must not hit the network.
        validate_model_provider_key("vLLM Embeddings", {"VLLM_EMBEDDINGS_API_BASE": BASE})
        mock_get.assert_not_called()


def test_probes_with_bearer_token_when_key_present():
    """Key present -> the endpoint is called with an Authorization: Bearer header."""
    resp = MagicMock(status_code=200)
    resp.raise_for_status.return_value = None
    with patch("requests.get", return_value=resp) as mock_get:
        validate_model_provider_key(
            "vLLM Embeddings",
            {"VLLM_EMBEDDINGS_API_BASE": BASE, "VLLM_EMBEDDINGS_API_KEY": "sk-real-key"},
        )
        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        assert kwargs["headers"].get("Authorization") == "Bearer sk-real-key"


def test_still_raises_on_real_auth_failure_when_key_present():
    """A genuinely rejected key (401 with the key sent) must still raise."""
    resp = MagicMock(status_code=401)
    with patch("requests.get", return_value=resp), pytest.raises(ValueError, match="Authentication failed"):
        validate_model_provider_key(
            "vLLM Embeddings",
            {"VLLM_EMBEDDINGS_API_BASE": BASE, "VLLM_EMBEDDINGS_API_KEY": "sk-wrong-key"},
        )
