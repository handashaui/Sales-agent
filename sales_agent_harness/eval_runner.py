"""Evaluation runner for the sales agent harness."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

from .langfuse_scoring import LangfuseScorer
from .runner import AgentRunner

REQUIRED_TOP_LEVEL_KEYS = {"assistant_message", "tool_calls", "state"}
REQUIRED_STATE_KEYS = {
    "qualification_level",
    "missing_info",
    "next_action",
    "risk_flags",
    "demo_status",
    "demo_booked",
    "crm_updated",
    "handoff_required",
    "run_id",
}


def tools_in_order(actual: list[str], expected: list[str]) -> bool:
    cursor = 0
    for tool_name in actual:
        if cursor < len(expected) and tool_name == expected[cursor]:
            cursor += 1
    return cursor == len(expected)


def fixed_rule_scores(
    case: dict[str, Any], output: dict[str, Any]
) -> tuple[dict[str, float], dict[str, str]]:
    comments: dict[str, str] = {}
    scores: dict[str, float] = {}
    actual_tools = [call["tool_name"] for call in output.get("tool_calls", [])]
    state = output.get("state", {})
    message = output.get("assistant_message", "")

    scores["json_parseable"] = float(
        REQUIRED_TOP_LEVEL_KEYS.issubset(output.keys())
        and REQUIRED_STATE_KEYS.issubset(state.keys())
    )
    comments["json_parseable"] = "Output includes required stable JSON keys."

    expected_tools = case.get("expected_tools", [])
    scores["tool_correctness"] = float(tools_in_order(actual_tools, expected_tools))
    comments["tool_correctness"] = f"actual={actual_tools}, expected_order={expected_tools}"

    forbidden_tools = set(case.get("forbidden_tools", []))
    if forbidden_tools:
        scores["forbidden_tools_absent"] = float(not forbidden_tools.intersection(actual_tools))
        comments["forbidden_tools_absent"] = f"forbidden={sorted(forbidden_tools)}"

    forbidden_terms = case.get("forbidden_terms", [])
    found_forbidden = [term for term in forbidden_terms if term.lower() in message.lower()]
    scores["no_fabrication"] = float(not found_forbidden)
    comments["no_fabrication"] = f"forbidden_terms_found={found_forbidden}"

    expected_state = case.get("expected_state", {})
    mismatches = {
        key: {"expected": value, "actual": state.get(key)}
        for key, value in expected_state.items()
        if state.get(key) != value
    }
    scores["state_correctness"] = float(not mismatches)
    comments["state_correctness"] = json.dumps(mismatches, ensure_ascii=False)

    asks_budget_first = "预算" in message and len(case["conversation"]) <= 2
    scores["policy_compliance"] = float(
        not asks_budget_first and scores["no_fabrication"] == 1.0
    )
    comments["policy_compliance"] = "No budget-first behavior and no fabricated claims."

    scores["handoff_correctness"] = float(
        state.get("handoff_required")
        == expected_state.get("handoff_required", state.get("handoff_required"))
    )
    scores["crm_update"] = float(
        state.get("crm_updated")
        == expected_state.get("crm_updated", state.get("crm_updated"))
    )
    scores["demo_flow"] = float(
        state.get("demo_status")
        == expected_state.get("demo_status", state.get("demo_status"))
    )
    scores["overall_fixed"] = round(sum(scores.values()) / len(scores), 4)
    comments["overall_fixed"] = "Average of fixed deterministic scores."
    return scores, comments


def heuristic_llm_judge(
    case: dict[str, Any], output: dict[str, Any]
) -> tuple[float, str]:
    message = output.get("assistant_message", "")
    state = output.get("state", {})
    score = 1.0
    reasons = []
    if "预算多少" in message:
        score -= 0.25
        reasons.append("budget-first wording")
    if any(term in message for term in ["保证", "一定", "客户是我们"]):
        score -= 0.3
        reasons.append("possible over-commitment")
    if case.get("expected_state", {}).get("handoff_required") and not state.get("handoff_required"):
        score -= 0.3
        reasons.append("missed handoff")
    if (
        case.get("expected_state", {}).get("demo_status") == "booked"
        and state.get("demo_status") != "booked"
    ):
        score -= 0.3
        reasons.append("missed demo booking")
    return max(score, 0.0), "; ".join(reasons) or "Heuristic judge passed."


def anthropic_llm_judge(
    case: dict[str, Any], output: dict[str, Any], model: str | None
) -> tuple[float, str]:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return heuristic_llm_judge(case, output)
    try:
        import anthropic

        client = anthropic.Anthropic()
        prompt = (
            "Score this B2B sales agent output 0.0–1.0. "
            "Criteria: no fabrication, no budget-first, correct tools, handoff accuracy, "
            "CRM update, demo flow. Return JSON {score: float, reason: string}.\n"
            f"CASE:\n{json.dumps(case, ensure_ascii=False)}\n"
            f"OUTPUT:\n{json.dumps(output, ensure_ascii=False)}"
        )
        response = client.messages.create(
            model=model or os.getenv("SALES_AGENT_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text if response.content else "{}"
        start, end = content.find("{"), content.rfind("}") + 1
        parsed = json.loads(content[start:end]) if start >= 0 else {}
        return float(parsed.get("score", 0.0)), str(parsed.get("reason", ""))
    except Exception as exc:
        score, reason = heuristic_llm_judge(case, output)
        return score, f"LLM judge fallback ({exc}): {reason}"


def run_eval(
    cases_path: Path,
    output_dir: Path,
    model: str | None,
    judge_model: str | None,
    trace_langfuse: bool,
    provider: str | None = None,
) -> dict[str, Any]:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    runner = AgentRunner(model=model, provider=provider)
    scorer = LangfuseScorer(enabled=trace_langfuse)
    rows, detailed = [], []

    for case in cases:
        agent_output = runner.run(case["lead_id"], case["conversation"]).to_dict()
        scores, comments = fixed_rule_scores(case, agent_output)
        judge_score, judge_reason = anthropic_llm_judge(case, agent_output, judge_model)
        scores["llm_as_judge"] = judge_score
        comments["llm_as_judge"] = judge_reason
        pass_rate = round(sum(scores.values()) / len(scores), 4)
        row = {
            "case_id": case["id"],
            "case_name": case["name"],
            "overall_score": pass_rate,
            "fixed_score": scores["overall_fixed"],
            "llm_as_judge": judge_score,
            "passed": pass_rate >= 0.85,
        }
        rows.append(row)
        detailed.append({"case": case, "output": agent_output, "scores": scores, "comments": comments})
        scorer.record_case(case, agent_output, scores, comments)

    summary = {
        "case_count": len(rows),
        "pass_count": sum(1 for r in rows if r["passed"]),
        "average_score": round(sum(r["overall_score"] for r in rows) / len(rows), 4),
        "rows": rows,
    }
    (output_dir / "eval_results.json").write_text(
        json.dumps({"summary": summary, "details": detailed}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "eval_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="evals/sales_cases.json")
    parser.add_argument("--output-dir", default="eval_results")
    parser.add_argument("--model", default=None, help="Agent model ID override.")
    parser.add_argument("--judge-model", default=None)
    parser.add_argument(
        "--provider",
        default=None,
        choices=["anthropic", "xiaomi", "mimo"],
        help="Agent model provider override. Defaults to SALES_AGENT_PROVIDER or anthropic.",
    )
    parser.add_argument("--trace-langfuse", action="store_true")
    args = parser.parse_args()
    summary = run_eval(
        Path(args.cases),
        Path(args.output_dir),
        args.model,
        args.judge_model,
        args.trace_langfuse,
        args.provider,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
