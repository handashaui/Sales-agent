"""AgentState — extends MessagesState with sales-specific structured fields."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal

from langgraph.graph import MessagesState
from langgraph.managed import RemainingSteps

QualificationLevel = Literal["low", "medium", "high", "unknown"]
DemoStatus = Literal["not_requested", "proposed", "blocked", "booked"]


class SalesAgentState(MessagesState):
    """Full state for the LangGraph ReAct sales agent.

    Structured fields are derived by runner.py from the tool-call trajectory
    after the agent finishes. They are NOT updated by tools mid-run.
    """

    remaining_steps: RemainingSteps

    # derived by runner from trajectory
    qualification_level: QualificationLevel
    missing_info: list[str]
    next_action: str
    risk_flags: Annotated[list[str], operator.add]
    demo_status: DemoStatus
    demo_booked: bool          # True only after book_demo returns success=True
    crm_updated: bool
    handoff_required: bool
    lead_context: dict[str, Any]
    run_id: str | None
