"""Optional real LLM helper for assistant message polishing."""

from __future__ import annotations

import json
import os
from typing import Any


def maybe_rewrite_message(
    *,
    enabled: bool,
    model: str | None,
    system_prompt: str,
    transcript: str,
    draft_message: str,
    state: dict[str, Any],
) -> str:
    """Use OpenAI to polish the assistant message without changing decisions."""

    if not enabled or not os.getenv("OPENAI_API_KEY"):
        return draft_message
    if os.getenv("SALES_AGENT_USE_REAL_LLM", "1") not in {"1", "true", "yes"}:
        return draft_message
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI()
        response = client.chat.completions.create(
            model=model or os.getenv("SALES_AGENT_MODEL", "gpt-4.1-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Rewrite only the assistant_message in concise Chinese. "
                        "Do not add prices, customer names, guarantees, or tool claims. "
                        "Keep the same next action and risk posture.\n"
                        f"TRANSCRIPT:\n{transcript}\n"
                        f"STATE:\n{json.dumps(state, ensure_ascii=False)}\n"
                        f"DRAFT:\n{draft_message}"
                    ),
                },
            ],
            temperature=0.2,
        )
        rewritten = response.choices[0].message.content
        return rewritten.strip() if rewritten else draft_message
    except Exception:
        return draft_message
