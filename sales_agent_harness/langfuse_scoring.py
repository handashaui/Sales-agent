"""Optional Langfuse trace and score integration."""

from __future__ import annotations

import os
from typing import Any


class LangfuseScorer:
    """Small compatibility wrapper around Langfuse SDK score APIs."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled and bool(
            os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
        )
        self.client = None
        if not self.enabled:
            return
        try:
            from langfuse import Langfuse  # type: ignore

            self.client = Langfuse(
                public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                host=os.getenv("LANGFUSE_HOST"),
            )
        except Exception:
            self.enabled = False
            self.client = None

    def record_case(
        self,
        case: dict[str, Any],
        output: dict[str, Any],
        scores: dict[str, float],
        comments: dict[str, str],
    ) -> None:
        if not self.enabled or self.client is None:
            return
        trace_id = output.get("state", {}).get("run_id") or case["id"]
        try:
            trace = self.client.trace(
                id=trace_id,
                name="sales_agent_eval_case",
                input=case,
                output=output,
                metadata={"case_id": case["id"], "case_name": case["name"]},
            )
            for name, value in scores.items():
                comment = comments.get(name, "")
                if hasattr(trace, "score"):
                    trace.score(name=name, value=value, comment=comment)
                elif hasattr(self.client, "score"):
                    self.client.score(
                        trace_id=trace_id, name=name, value=value, comment=comment
                    )
            if hasattr(self.client, "flush"):
                self.client.flush()
        except Exception:
            return
