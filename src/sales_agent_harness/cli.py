"""Command line interface for the sales agent harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import SalesAgent


def run_payload(payload: dict, prompt_version: str, model: str | None) -> dict:
    agent = SalesAgent(prompt_version=prompt_version, model=model, prefer_real_llm=True)
    output = agent.run(
        lead_id=payload["lead_id"],
        conversation=payload["conversation"],
        run_id=payload.get("run_id"),
    )
    return output.to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Sales Agent Harness.")
    parser.add_argument("--input", "-i", help="Input JSON file. Defaults to stdin.")
    parser.add_argument("--output", "-o", help="Output JSON file. Defaults to stdout.")
    parser.add_argument("--prompt-version", default="v1")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    if args.input:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    else:
        payload = json.loads(sys.stdin.read())

    result = run_payload(payload, args.prompt_version, args.model)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
