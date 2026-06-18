# vLLM providers have no static model catalog — models are fetched live from
# the user's vLLM server once VLLM_API_BASE is configured.
# replace_with_live_models() populates these at runtime via GET /v1/models.
# The fallback loops in list_models and get_enabled_models ensure both
# providers remain visible in the UI even before configuration.
VLLM_MODELS_DETAILED: list = []

VLLM_EMBEDDING_MODELS_DETAILED: list = []
