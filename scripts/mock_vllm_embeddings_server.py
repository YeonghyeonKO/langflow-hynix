"""Mock vLLM Embeddings server (port 8001) with embedding-only models.

Separate from mock_vllm_server.py (port 8100) which serves LLM models.
"""

import argparse
import json
import random
from http.server import BaseHTTPRequestHandler, HTTPServer

MOCK_MODELS = {
    "object": "list",
    "data": [
        {"id": "BAAI/bge-m3", "object": "model", "owned_by": "vllm"},
        {"id": "intfloat/multilingual-e5-large-instruct", "object": "model", "owned_by": "vllm"},
    ],
}

EMBEDDING_DIM = 1024


def fake_embedding():
    return [round(random.uniform(-0.05, 0.05), 8) for _ in range(EMBEDDING_DIM)]


class MockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/v1/models", "/models"):
            self._json_response(MOCK_MODELS)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path in ("/v1/embeddings", "/embeddings"):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            raw_input = body.get("input", "")
            if isinstance(raw_input, str):
                inputs = [raw_input]
            elif isinstance(raw_input, list) and raw_input and isinstance(raw_input[0], list):
                inputs = raw_input
            elif isinstance(raw_input, list):
                inputs = raw_input
            else:
                inputs = [str(raw_input)]
            model = body.get("model", "mock-model")
            data = [
                {"object": "embedding", "index": i, "embedding": fake_embedding()}
                for i in range(len(inputs))
            ]
            total_tokens = sum(
                len(t.split()) if isinstance(t, str) else len(t) if isinstance(t, list) else 1
                for t in inputs
            )
            self._json_response({
                "object": "list",
                "data": data,
                "model": model,
                "usage": {"prompt_tokens": total_tokens, "total_tokens": total_tokens},
            })
        else:
            self.send_response(404)
            self.end_headers()

    def _json_response(self, obj, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def log_message(self, format, *args):
        print(f"[mock-vllm-emb] {args[0]}")


def main():
    parser = argparse.ArgumentParser(description="Mock vLLM Embeddings server")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), MockHandler)
    print(f"Mock vLLM Embeddings server on http://localhost:{args.port}")
    print(f"  GET  /v1/models     → bge-m3, multilingual-e5")
    print(f"  POST /v1/embeddings → {EMBEDDING_DIM}-dim fake vectors")
    server.serve_forever()


if __name__ == "__main__":
    main()
