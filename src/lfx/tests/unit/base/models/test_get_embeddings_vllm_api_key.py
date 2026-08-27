"""Issue #33 — get_embeddings must not use the vLLM base URL as the API key.

vLLM providers declare their API *base URL* as the first (required, non-secret)
variable and the API key as an optional secret. ``get_model_provider_variable_mapping()``
selects each provider's first *required secret*; vLLM has none, so it falls back to the
first variable — the base URL. The generic ``get_api_key_for_provider()`` then returns
``VLLM_EMBEDDINGS_API_BASE`` as if it were the key, producing a malformed
``Authorization: Bearer http://common.llm.skhynix.com`` header during Knowledge Base
embedding ingestion.

These tests pin the fixed behavior:

- No key configured  -> ``api_key == "dummy"``
- Key configured     -> ``api_key == <the configured key>``

and in both cases ``base_url == VLLM_EMBEDDINGS_API_BASE + "/v1"``.
"""

from __future__ import annotations

from unittest.mock import patch

import lfx.base.models.unified_models as unified_models_module
from lfx.base.models.unified_models.instantiation import get_embeddings

BASE_URL = "http://common.llm.skhynix.com"


class _CapturingEmbeddings:
    """Stand-in embedding class that records the kwargs it was constructed with."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs


def _model() -> list[dict]:
    return [
        {
            "name": "bge-m3",
            "provider": "vLLM Embeddings",
            "metadata": {
                "embedding_class": "OpenAIEmbeddings",
                "param_mapping": {
                    "model": "model",
                    "api_key": "api_key",
                    "api_base": "base_url",
                },
            },
        }
    ]


def _run(provider_vars: dict[str, str]) -> dict:
    """Instantiate embeddings for vLLM Embeddings and return the captured kwargs.

    ``get_api_key_for_provider`` is patched to return the base URL — reproducing the
    buggy resolver output — so the test proves the fix bypasses it for vLLM instead of
    merely happening to receive a good value.
    """
    with (
        patch.object(unified_models_module, "get_embedding_class", return_value=_CapturingEmbeddings),
        patch.object(unified_models_module, "get_all_variables_for_provider", return_value=provider_vars),
        patch.object(unified_models_module, "get_api_key_for_provider", return_value=BASE_URL),
        patch.dict("os.environ", {}, clear=True),
    ):
        instance = get_embeddings(model=_model(), user_id="00000000-0000-0000-0000-000000000000")
    return instance.kwargs


def test_uses_dummy_key_when_vllm_embeddings_api_key_not_configured():
    """No VLLM_EMBEDDINGS_API_KEY -> api_key falls back to 'dummy', never the base URL."""
    kwargs = _run({"VLLM_EMBEDDINGS_API_BASE": BASE_URL})

    assert kwargs["api_key"] == "dummy"
    assert kwargs["api_key"] != BASE_URL
    assert kwargs["base_url"] == f"{BASE_URL}/v1"


def test_uses_configured_key_when_vllm_embeddings_api_key_present():
    """VLLM_EMBEDDINGS_API_KEY configured -> that key is used, base URL still separate."""
    kwargs = _run(
        {
            "VLLM_EMBEDDINGS_API_BASE": BASE_URL,
            "VLLM_EMBEDDINGS_API_KEY": "sk-real-vllm-key",
        }
    )

    assert kwargs["api_key"] == "sk-real-vllm-key"
    assert kwargs["base_url"] == f"{BASE_URL}/v1"
