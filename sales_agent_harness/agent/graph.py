"""Build the LangGraph ReAct sales agent.

Usage:
    agent = build_agent()
    result = agent.invoke({"messages": messages}, config={"callbacks": [...]})
"""

from __future__ import annotations

import os
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from ..tools import all_tools
from .state import SalesAgentState


def build_agent(
    model: str | None = None,
    provider: str | None = None,
    callbacks: list[Any] | None = None,
) -> Any:
    """Return a compiled LangGraph ReAct agent.

    Pass `callbacks` (e.g. a Langfuse CallbackHandler) to wire up tracing
    without modifying this function.
    """
    resolved_provider = (provider or os.getenv("SALES_AGENT_PROVIDER", "anthropic")).lower()

    if resolved_provider in {"xiaomi", "mimo"}:
        resolved_model = model or os.getenv("SALES_AGENT_MODEL", "mimo-v2.5-pro")
        api_key = os.getenv("XIAOMI_API_KEY") or os.getenv("MIMO_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Missing Xiaomi MiMo API key. Set XIAOMI_API_KEY or MIMO_API_KEY."
            )
        llm = ChatOpenAI(
            model=resolved_model,
            api_key=api_key,
            base_url=os.getenv("XIAOMI_BASE_URL", "https://api.xiaomimimo.com/v1"),
            temperature=0.1,
        )
    elif resolved_provider == "anthropic":
        resolved_model = model or os.getenv("SALES_AGENT_MODEL", "claude-sonnet-4-6")
        llm = ChatAnthropic(model=resolved_model, temperature=0.1)
    else:
        raise ValueError(
            f"Unsupported SALES_AGENT_PROVIDER={resolved_provider!r}. "
            "Use 'anthropic' or 'xiaomi'."
        )

    agent = create_react_agent(
        model=llm,
        tools=all_tools,
        state_schema=SalesAgentState,
    )
    return agent
