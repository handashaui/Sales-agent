# Evaluation Summary

Command:

```bash
PYTHONPATH=src python -m sales_agent_harness.eval_runner \
  --cases evals/sales_cases.json \
  --output-dir eval_results
```

Latest local result:

```text
case_count=12
pass_count=12
average_score=1.0
```

The suite covers:

- policy compliance;
- correct tool calls;
- no fabricated pricing, customer references, ROI, or commitments;
- human handoff;
- CRM updates;
- Demo booking;
- JSON stability;
- multi-turn state handling.

Langfuse:

- fixed rule scores are emitted per case when `--trace-langfuse` is enabled;
- LLM-as-judge uses OpenAI when `OPENAI_API_KEY` is set;
- otherwise the runner uses a deterministic heuristic judge fallback.
