"""Tool: write_crm_note — persist a structured CRM note for a lead."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ._db import append_json

QualificationLevel = Literal["low", "medium", "high", "unknown"]


class WriteCRMNoteArgs(BaseModel):
    lead_id: str = Field(description="CRM lead identifier.")
    summary: str = Field(
        description=(
            "Plain-text summary of this interaction: pain points discussed, "
            "intent signals, and key facts collected. Do NOT claim the demo is "
            "booked unless book_demo already returned success=true."
        )
    )
    qualification_level: QualificationLevel = Field(
        description=(
            "Lead quality based on conversation: 'high' (clear pain + fit + intent), "
            "'medium' (partial signals), 'low' (student/irrelevant), 'unknown' (insufficient info)."
        )
    )
    next_action: str = Field(
        description=(
            "Concrete next step, e.g. 'demo_booked', 'clarify', 'handoff_to_human', "
            "'ask_for_email', 'continue_qualification', 'clarify_or_handoff'."
        )
    )


@tool(args_schema=WriteCRMNoteArgs)
def write_crm_note(
    lead_id: str,
    summary: str,
    qualification_level: QualificationLevel,
    next_action: str,
) -> dict[str, Any]:
    """Append a structured CRM note for the lead. Call after every substantive
    interaction: after qualifying, after booking a demo, after a sensitive claim
    is avoided, and after a human handoff is triggered. Required fields ensure the
    note captures pain points, qualification stage, and next step."""
    note = {
        "note_id": f"crm-{lead_id}-{int(datetime.now(timezone.utc).timestamp())}",
        "lead_id": lead_id,
        "summary": summary,
        "qualification_level": qualification_level,
        "next_action": next_action,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    append_json(f"crm/notes/{lead_id}.json", note)
    return {"saved": True, "note_id": note["note_id"], "lead_id": lead_id}
