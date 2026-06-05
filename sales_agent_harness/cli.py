"""CLI entry point for running one sales-agent request."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import AgentRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Sales Agent Harness.")
    parser.add_argument("--input", "-i", help="Input JSON file. Defaults to stdin.")
    parser.add_argument("--output", "-o", help="Output JSON file. Defaults to stdout.")
    parser.add_argument("--model", default=None, help="Model ID override.")
    parser.add_argument(
        "--provider",
        default=None,
        choices=["anthropic", "xiaomi", "mimo"],
        help="Model provider override. Defaults to SALES_AGENT_PROVIDER or anthropic.",
    )
    args = parser.parse_args()

    payload = (
        json.loads(Path(args.input).read_text(encoding="utf-8"))
        if args.input
        else json.loads(sys.stdin.read())
    )

    result = AgentRunner(model=args.model, provider=args.provider).run(
        lead_id=payload["lead_id"],
        conversation=payload["conversation"],
        run_id=payload.get("run_id"),
    ).to_dict()

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0
