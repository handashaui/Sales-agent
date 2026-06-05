"""Tool: handoff_to_human — escalate lead to a human sales rep."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ._db import write_json

Urgency = Literal["low", "normal", "high"]


class HandoffArgs(BaseModel):
    lead_id: str = Field(description="CRM lead identifier.")
    reason: str = Field(
        description=(
            "Why a human is needed. Use one of: 'user_requested_human', "
            "'requires_contract_review', 'requires_pricing_commitment', "
            "'requires_legal_or_compliance', 'requires_procurement_process'."
        )
    )
    urgency: Urgency = Field(
        default="normal",
        description="Urgency level: 'high' if the user explicitly asked for a human now.",
    )


@tool(args_schema=HandoffArgs)
def handoff_to_human(
    lead_id: str,
    reason: str,
    urgency: Urgency = "normal",
) -> dict[str, Any]:
    """Escalate the conversation to a human sales representative. Call when the user
    requests a human, asks for contract/legal/procurement commitments, or requires
    custom pricing. After calling this tool, stop making promises and close the
    conversation gracefully."""
    ts = int(datetime.now(timezone.utc).timestamp())
    handoff_id = f"handoff-{lead_id}-{ts}"
    record = {
        "handoff_id": handoff_id,
        "lead_id": lead_id,
        "reason": reason,
        "urgency": urgency,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(f"handoffs/{handoff_id}.json", record)
    return {
        "queued": True,
        "handoff_id": handoff_id,
        "lead_id": lead_id,
        "reason": reason,
    }
