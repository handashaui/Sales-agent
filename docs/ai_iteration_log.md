# AI Iteration Log

## Iteration 1: Baseline Harness

Built the initial package, state dataclasses, CLI, and mock tool registry. The
first demo request returned stable JSON and completed the calendar -> booking ->
CRM flow.

Finding: generated Python bytecode was accidentally staged after CLI smoke
testing.

Change: added `.gitignore` and removed generated files from the Git index.

## Iteration 2: Evaluation Coverage

Added 12 eval cases covering manufacturing qualification, demo booking, missing
email, pricing, customer references, handoff, low-quality leads, timezone
handling, JSON stability, and multi-turn qualification.

Finding: some CRM note calls were present in internal trajectory but missing from
public `tool_calls`.

Change: passed the public tool call accumulator through CRM note writes for
sensitive-claim and handoff paths.

Result: eval improved from passing with partial fixed scores to fuller tool-call
traceability.

## Iteration 3: Policy And Qualification Fixes

Ran the eval suite and found two weaker fixed scores:

- student/research lead was routed into business qualification;
- large company with no budget but clear pain was only `medium`.

Changes:

- low-intent student/research leads now stay in `clarify`;
- leads with large company size, sales context, and clear pain qualify as `high`
  even when budget is not defined.

Result:

```text
case_count=12
pass_count=12
average_score=1.0
```

## Iteration 4: Real-LLM And Observability Hooks

Added optional OpenAI message rewriting while keeping tool and state decisions
deterministic. Added optional Langfuse scoring wrapper for fixed scores and
LLM-as-judge output.

Rationale: this demonstrates how AI can be used in the loop without making eval
results flaky.
