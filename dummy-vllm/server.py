"""Dummy vLLM-compatible OpenAI API server for local testing.

Exposes:
  GET  /v1/models              — list available models
  POST /v1/chat/completions    — chat completions (vLLM Language)
  POST /v1/embeddings          — embeddings (vLLM Embedding)

Run:
  pip install fastapi uvicorn
  python server.py
"""

import time
import uuid

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Dummy vLLM API")

LANGUAGE_MODELS = ["dummy-llm-7b", "dummy-llm-13b"]
EMBEDDING_MODELS = ["dummy-embed-v1"]
ALL_MODELS = LANGUAGE_MODELS + EMBEDDING_MODELS


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": model_id,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "dummy-vllm",
            }
            for model_id in ALL_MODELS
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", LANGUAGE_MODELS[0])
    messages = body.get("messages", [])
    last_msg = messages[-1]["content"] if messages else ""

    reply = f"[Dummy vLLM] 모델 '{model}' 응답: '{last_msg[:80]}' 에 대한 테스트 응답입니다."

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


@app.post("/v1/embeddings")
async def embeddings(request: Request):
    body = await request.json()
    model = body.get("model", EMBEDDING_MODELS[0])
    input_data = body.get("input", [])
    if isinstance(input_data, str):
        input_data = [input_data]

    # Return 1536-dim zero vectors (matches OpenAI text-embedding-ada-002 dim)
    return {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "index": i,
                "embedding": [0.0] * 1536,
            }
            for i in range(len(input_data))
        ],
        "model": model,
        "usage": {"prompt_tokens": len(input_data) * 5, "total_tokens": len(input_data) * 5},
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
