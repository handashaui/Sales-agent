"""AgentRunner — input JSON → LangGraph agent → output JSON.

Input:  { lead_id, conversation: [{role, content}], run_id? }
Output: { assistant_message, tool_calls: [{tool_name, arguments, result}], state }

State is derived deterministically from the tool-call trajectory; no LLM judgement
is involved in computing state fields.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from .agent.graph import build_agent
from .agent.prompt import get_system_prompt

# ---------------------------------------------------------------------------
# Public I/O contract types (one file, no separate schemas.py needed)
# ---------------------------------------------------------------------------

QualificationLevel = Literal["low", "medium", "high", "unknown"]
DemoStatus = Literal["not_requested", "proposed", "blocked", "booked"]


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None = None
    timestamp: str | None = None


class AgentStateOutput(BaseModel):
    qualification_level: QualificationLevel = "unknown"
    missing_info: list[str] = Field(default_factory=list)
    next_action: str = "clarify"
    risk_flags: list[str] = Field(default_factory=list)
    demo_status: DemoStatus = "not_requested"
    demo_booked: bool = False
    crm_updated: bool = False
    handoff_required: bool = False
    run_id: str | None = None


class AgentOutput(BaseModel):
    assistant_message: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    state: AgentStateOutput = Field(default_factory=AgentStateOutput)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_messages(lead_id: str, conversation: list[ConversationTurn]) -> list[BaseMessage]:
    messages: list[BaseMessage] = [SystemMessage(content=get_system_prompt(lead_id))]
    for turn in conversation:
        if turn.role == "user":
            messages.append(HumanMessage(content=turn.content))
        elif turn.role == "assistant":
            messages.append(AIMessage(content=turn.content))
    return messages


def _extract_trajectory(messages: list[BaseMessage]) -> list[ToolCallRecord]:
    results: dict[str, Any] = {}
    for msg in messages:
        if hasattr(msg, "tool_call_id") and msg.tool_call_id:
            raw = msg.content
            try:
                results[msg.tool_call_id] = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, TypeError):
                results[msg.tool_call_id] = {"raw": str(raw)}

    ts = datetime.now(timezone.utc).isoformat()
    trajectory: list[ToolCallRecord] = []
    for msg in messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                trajectory.append(ToolCallRecord(
                    tool_name=tc["name"],
                    arguments=tc["args"],
                    result=results.get(tc["id"]),
                    timestamp=ts,
                ))
    return trajectory


def _derive_state(trajectory: list[ToolCallRecord], run_id: str) -> AgentStateOutput:
    """Build output state from tool trajectory.

    Guards enforced here (not in prompt):
    - demo_booked only True when book_demo returned success=True
    - risk_flag if write_crm_note claims '已预约' before demo is confirmed
    """
    state = AgentStateOutput(run_id=run_id)

    for record in trajectory:
        name = record.tool_name
        args = record.arguments or {}
        result = record.result or {}

        if name == "book_demo":
            if result.get("success"):
                state.demo_booked = True
                state.demo_status = "booked"
                state.next_action = "demo_booked"
            else:
                state.demo_status = "blocked"

        elif name == "check_calendar":
            if state.demo_status == "not_requested":
                state.demo_status = "proposed"

        elif name == "write_crm_note":
            state.crm_updated = True
            ql = args.get("qualification_level")
            if ql in ("low", "medium", "high", "unknown"):
                state.qualification_level = ql  # type: ignore[assignment]
            na = args.get("next_action")
            if na:
                state.next_action = na
            # Guard: must not claim 已预约 before demo is confirmed
            if "已预约" in args.get("summary", "") and not state.demo_booked:
                state.risk_flags.append("crm_note_claimed_booked_before_demo_confirmed")

        elif name == "handoff_to_human":
            state.handoff_required = True
            state.next_action = "handoff_to_human"

    if state.qualification_level == "unknown" and not state.crm_updated:
        state.missing_info = ["company_profile", "pain_point"]

    return state


# ---------------------------------------------------------------------------
# AgentRunner
# ---------------------------------------------------------------------------

class AgentRunner:
    def __init__(
        self,
        model: str | None = None,
        provider: str | None = None,
        callbacks: list[Any] | None = None,
    ) -> None:
        self._agent = build_agent(model=model, provider=provider, callbacks=callbacks)
        self._callbacks = callbacks or []

    def run(
        self,
        lead_id: str,
        conversation: list[dict[str, str]] | list[ConversationTurn],
        run_id: str | None = None,
        **_kwargs: Any,
    ) -> AgentOutput:
        run_id = run_id or str(uuid.uuid4())
        turns = [
            t if isinstance(t, ConversationTurn) else ConversationTurn(**t)
            for t in conversation
        ]
        messages = _build_messages(lead_id, turns)
        config = {"callbacks": self._callbacks} if self._callbacks else None
        result = self._agent.invoke({"messages": messages}, config=config)

        trajectory = _extract_trajectory(result["messages"])
        state = _derive_state(trajectory, run_id=run_id)

        final_msg = ""
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                final_msg = msg.content if isinstance(msg.content, str) else str(msg.content)
                break

        return AgentOutput(assistant_message=final_msg, tool_calls=trajectory, state=state)
