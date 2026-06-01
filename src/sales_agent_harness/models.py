"""Typed data structures for the sales agent harness."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

QualificationLevel = Literal["low", "medium", "high", "unknown"]


@dataclass
class ConversationTurn:
    role: Literal["user", "assistant", "system"]
    content: str


@dataclass
class ToolCallRecord:
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
        }


@dataclass
class AgentState:
    qualification_level: QualificationLevel = "unknown"
    missing_info: list[str] = field(default_factory=list)
    next_action: str = "clarify"
    risk_flags: list[str] = field(default_factory=list)
    demo_status: Literal["not_requested", "proposed", "booked", "blocked"] = (
        "not_requested"
    )
    crm_updated: bool = False
    handoff_required: bool = False
    lead_context: dict[str, Any] = field(default_factory=dict)
    trajectory: list[ToolCallRecord] = field(default_factory=list)
    run_id: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "qualification_level": self.qualification_level,
            "missing_info": self.missing_info,
            "next_action": self.next_action,
            "risk_flags": self.risk_flags,
            "demo_status": self.demo_status,
            "crm_updated": self.crm_updated,
            "handoff_required": self.handoff_required,
            "run_id": self.run_id,
        }


@dataclass
class AgentOutput:
    assistant_message: str
    tool_calls: list[ToolCallRecord]
    state: AgentState

    def to_dict(self) -> dict[str, Any]:
        return {
            "assistant_message": self.assistant_message,
            "tool_calls": [call.to_public_dict() for call in self.tool_calls],
            "state": self.state.to_public_dict(),
        }

    def to_trace_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        data["trajectory"] = [asdict(call) for call in self.state.trajectory]
        return data
