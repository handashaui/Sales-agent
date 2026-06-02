"""Tiny stdlib HTTP service for the sales agent harness."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from .agent import SalesAgent


class SalesAgentHandler(BaseHTTPRequestHandler):
    agent = SalesAgent()

    def do_POST(self) -> None:
        if self.path != "/run":
            self.send_error(404, "Use POST /run")
            return
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        output = self.agent.run(payload["lead_id"], payload["conversation"]).to_dict()
        body = json.dumps(output, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the Sales Agent Harness.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), SalesAgentHandler)
    print(f"Sales Agent Harness listening on http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
