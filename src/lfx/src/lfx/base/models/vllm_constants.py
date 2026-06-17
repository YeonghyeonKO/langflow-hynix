from .model_metadata import create_model_metadata

# Placeholder entries so the vLLM providers appear in the Model Providers
# settings UI before the user has configured a server URL.
# replace_with_live_models() replaces these at runtime with the models
# actually loaded on the user's vLLM server.
VLLM_MODELS_DETAILED = [
    create_model_metadata(
        provider="vLLM",
        name="ibm-granite/granite-3.3-8b-instruct",
        icon="vLLM",
        tool_calling=True,
        default=True,
    ),
]

VLLM_EMBEDDING_MODELS_DETAILED = [
    create_model_metadata(
        provider="vLLM Embeddings",
        name="BAAI/bge-large-en-v1.5",
        icon="vLLM",
        model_type="embeddings",
        default=True,
    ),
]
