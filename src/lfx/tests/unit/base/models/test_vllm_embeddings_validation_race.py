"""Issue #34 — vLLM Embedding credential validation must not 401 during the save race.

The provider modal saves VLLM_EMBEDDINGS_API_BASE and VLLM_EMBEDDINGS_API_KEY concurrently.
The base-URL save (the provider's primary variable, so the one that triggers backend
validation) re-reads the key from the DB, which may not be committed yet. Before the fix,
the two-step probe in ``_validate_vllm_endpoint`` saw an auth-enforcing server with no key
and raised "requires an API key but none was provided" — a spurious first-attempt failure
that clears on retry once the key commits.

These tests pin the fixed behavior:

- Auth-enforcing server, no key yet  -> skip (no raise, no step-2 call).
- Auth-enforcing server, key present -> step 2 sends the bearer token.
- Auth-enforcing server, wrong key    -> still raises "Authentication failed".
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from lfx.base.models.unified_models.credentials import validate_model_provider_key

BASE = "http://common.llm.skhynix.com"


def _resp(status: int) -> MagicMock:
    r = MagicMock(status_code=status)
    r.raise_for_status.return_value = None
    return r


def test_skips_when_auth_enforced_but_key_not_yet_available():
    """Step 1 = 401 (auth enforced) and no key -> skip instead of raising (save-race)."""
    with patch("requests.get", return_value=_resp(401)) as mock_get:
        # Must not raise; must not attempt a step-2 authenticated probe.
        validate_model_provider_key("vLLM Embedding", {"VLLM_EMBEDDINGS_API_BASE": BASE})
        assert mock_get.call_count == 1  # only the unauthenticated step 1 ran


def test_sends_bearer_on_step_two_when_key_present():
    """Step 1 = 401, key present -> step 2 probes with Authorization: Bearer and passes."""
    with patch("requests.get", side_effect=[_resp(401), _resp(200)]) as mock_get:
        validate_model_provider_key(
            "vLLM Embedding",
            {"VLLM_EMBEDDINGS_API_BASE": BASE, "VLLM_EMBEDDINGS_API_KEY": "sk-real-key"},
        )
        assert mock_get.call_count == 2
        _, kwargs = mock_get.call_args  # step 2
        assert kwargs["headers"].get("Authorization") == "Bearer sk-real-key"


def test_still_raises_on_real_auth_failure_when_key_present():
    """Step 1 = 401, wrong key -> step 2 also 401 -> must raise."""
    with (
        patch("requests.get", side_effect=[_resp(401), _resp(401)]),
        pytest.raises(ValueError, match="Authentication failed"),
    ):
        validate_model_provider_key(
            "vLLM Embedding",
            {"VLLM_EMBEDDINGS_API_BASE": BASE, "VLLM_EMBEDDINGS_API_KEY": "sk-wrong-key"},
        )
