# Sales Agent Harness

Minimal sales Agent Harness for lead follow-up, tool execution, state
management, trajectory logging, and automated evaluation.

The implementation is intentionally small and runnable from the command line. It
uses a DeerFlow-style shape: a named sales agent, versioned system prompt,
structured state, registered tools, deterministic policy routing, optional real
LLM message polishing, and optional Langfuse scoring.

## What It Does

- Qualifies B2B sales leads without over-focusing on budget.
- Clarifies missing information when needed.
- Uses mock tools for lead context, knowledge search, calendar, demo booking,
  CRM notes, and human handoff.
- Returns stable JSON with `assistant_message`, `tool_calls`, and `state`.
- Tracks tool trajectory and `run_id` for observability.
- Runs 12 automated eval cases with fixed scoring and optional LLM-as-judge.
- Generates an Excel workbook for the eval test set and results.

## Assignment Submission Materials

This repository is prepared for the AI Harness / Agent developer written test.
It contains both the runnable harness and the required written materials:

- First part answer: `docs/销售agent故障诊断与重构.md`
  - Diagnoses the broken sales-agent conversations.
  - Summarizes the planned agent improvements, tool-use strategy, test examples,
    and prompt iteration notes.
  - Supporting notes copied from the Obsidian vault:
    - `docs/sales system prompt.md`
    - `docs/tool use strategy.md`
    - `docs/test examples.md`
    - `docs/prompt iteration.md`
- AI collaboration log: `docs/AI协作全过程日志.md`
  - Records the AI tools used, problem decomposition, key prompts, iterations,
    validation process, AI-output errors, and final reflection.
- Runnable agent harness:
  - `src/sales_agent_harness/agent.py`
  - `src/sales_agent_harness/tools.py`
  - `src/sales_agent_harness/cli.py`
  - `src/sales_agent_harness/service.py`
- Evaluation runner and test set:
  - `src/sales_agent_harness/eval_runner.py`
  - `evals/sales_cases.json`
  - `evals/sales_agent_eval_cases.xlsx`
- Additional evaluation notes: `docs/eval_summary.md`
- Earlier concise iteration note: `docs/ai_iteration_log.md`

The current solution's three largest risks are:

- The knowledge base, CRM, and calendar are mock implementations, so integration
  failures and API edge cases are not fully covered.
- The deterministic policy is intentionally small and may miss unusual user
  wording outside the evaluation set.
- Real LLM usage only rewrites the final assistant message; full LLM-driven tool
  planning would require stricter guardrails and broader eval coverage before
  production use.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,real-llm,observability,excel]"
```

The core CLI works with no required third-party runtime dependencies. Optional
extras enable OpenAI, Langfuse, pytest, and Excel generation.

## Environment

Real LLM usage is optional and only activates when credentials are present.

```bash
export OPENAI_API_KEY="..."
export SALES_AGENT_MODEL="gpt-4.1-mini"
export SALES_AGENT_USE_REAL_LLM=1

export LANGFUSE_PUBLIC_KEY="..."
export LANGFUSE_SECRET_KEY="..."
export LANGFUSE_HOST="https://cloud.langfuse.com"
```

Do not commit API keys. A missing key falls back to deterministic local behavior
for the agent and heuristic judging for eval.

## Run The Agent

```bash
PYTHONPATH=src python -m sales_agent_harness.cli \
  --input examples/demo_request.json
```

Example output:

```json
{
  "assistant_message": "好的，已为你安排 周二 10:00 SGT 的 Demo...",
  "tool_calls": [
    {"tool_name": "get_lead_context", "arguments": {"lead_id": "L-DEMO"}},
    {"tool_name": "check_calendar", "arguments": {"timezone_name": "Asia/Singapore", "duration_minutes": 30}},
    {"tool_name": "book_demo", "arguments": {"lead_id": "L-DEMO", "slot_id": "sg-tue-1000", "email": "alex@demo.com", "timezone_name": "Asia/Singapore"}},
    {"tool_name": "write_crm_note", "arguments": {"lead_id": "L-DEMO", "summary": "Demo booked...", "qualification_level": "high", "next_action": "demo_booked"}}
  ],
  "state": {
    "qualification_level": "high",
    "missing_info": ["company_profile", "sales_team_size", "pain_point"],
    "next_action": "demo_booked",
    "risk_flags": [],
    "demo_status": "booked",
    "crm_updated": true,
    "handoff_required": false,
    "run_id": "..."
  }
}
```

## Run As A Simple Service

```bash
PYTHONPATH=src python -m sales_agent_harness.service --port 8080
```

Then call:

```bash
curl -X POST http://127.0.0.1:8080/run \
  -H "content-type: application/json" \
  -d @examples/demo_request.json
```

## Run Eval

```bash
PYTHONPATH=src python -m sales_agent_harness.eval_runner \
  --cases evals/sales_cases.json \
  --output-dir eval_results
```

With Langfuse tracing and scoring:

```bash
PYTHONPATH=src python -m sales_agent_harness.eval_runner \
  --cases evals/sales_cases.json \
  --output-dir eval_results \
  --trace-langfuse \
  --judge-model "$SALES_AGENT_MODEL"
```

The runner writes:

- `eval_results/eval_results.json`
- `eval_results/eval_summary.csv`
- Langfuse trace scores when credentials are configured

Current local result:

```text
case_count=12
pass_count=12
average_score=1.0
```

## Generate Excel Test Set

```bash
python scripts/generate_eval_excel.py \
  --cases evals/sales_cases.json \
  --eval-results eval_results/eval_results.json \
  --output evals/sales_agent_eval_cases.xlsx
```

Workbook sheets:

- `cases`
- `expected_tools`
- `rubric`
- `eval_results`

## Architecture

```text
JSON input
  -> SalesAgent.run
    -> versioned system prompt
    -> deterministic policy/state router
    -> MockToolRuntime registry
    -> optional OpenAI message rewrite
  -> AgentOutput JSON
  -> eval runner
    -> fixed rule scores
    -> optional OpenAI LLM-as-judge
    -> optional Langfuse trace/score
```

Important modules:

- `src/sales_agent_harness/agent.py`: stateful agent orchestration.
- `src/sales_agent_harness/tools.py`: mock tool runtime.
- `src/sales_agent_harness/eval_runner.py`: fixed and LLM judge eval.
- `src/sales_agent_harness/langfuse_scoring.py`: optional Langfuse SDK wrapper.
- `evals/sales_cases.json`: 12-case test set.

## Scoring Dimensions

- Policy compliance.
- Correct tool calls and tool order.
- No fabricated pricing, customer cases, ROI, or commitments.
- Correct human handoff.
- Correct CRM updates.
- Demo booking flow completion.
- Stable, parseable JSON.
- Optional LLM-as-judge score.

## Known Issues

- The repository could not be cloned from GitHub in the sandbox because network
  access and `gh` login were unavailable. This implementation was prepared in a
  local repo with the intended `origin` remote set to
  `https://github.com/handashaui/Sales-agent.git`.
- Langfuse documentation could not be fetched due the same network restriction,
  so the SDK wrapper is defensive and optional. It should be verified once
  network access is available.
- Real LLM use only rewrites the final assistant message. Tool routing and state
  transitions remain deterministic to keep eval stable.
- Mock calendar and CRM are in-memory only.
