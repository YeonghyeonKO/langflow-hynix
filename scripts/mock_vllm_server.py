"""Mock vLLM server for local testing.

Returns fake model list on GET /v1/models (OpenAI-compatible format).
Usage: python scripts/mock_vllm_server.py [--port 8000]
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


MOCK_MODELS = {
    "object": "list",
    "data": [
        {"id": "ibm-granite/granite-3.3-8b-instruct", "object": "model", "owned_by": "vllm"},
        {"id": "ibm-granite/granite-3.3-2b-instruct", "object": "model", "owned_by": "vllm"},
        {"id": "meta-llama/Llama-3.1-8B-Instruct", "object": "model", "owned_by": "vllm"},
        {"id": "BAAI/bge-large-en-v1.5", "object": "model", "owned_by": "vllm"},
        {"id": "intfloat/multilingual-e5-large-instruct", "object": "model", "owned_by": "vllm"},
    ],
}


class MockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/v1/models", "/models"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(MOCK_MODELS).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[mock-vllm] {args[0]}")


def main():
    parser = argparse.ArgumentParser(description="Mock vLLM server")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), MockHandler)
    print(f"Mock vLLM server running on http://localhost:{args.port}")
    print(f"  GET /v1/models → {len(MOCK_MODELS['data'])} models")
    server.serve_forever()


if __name__ == "__main__":
    main()
