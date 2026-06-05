"""Tool: get_lead_context — fetch CRM lead profile."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ._db import load_json


class GetLeadContextArgs(BaseModel):
    lead_id: str = Field(
        description="CRM lead identifier, e.g. 'L123'. Always call this first."
    )


@tool(args_schema=GetLeadContextArgs)
def get_lead_context(lead_id: str) -> dict[str, Any]:
    """Retrieve existing CRM context for a lead: company profile, industry, region, size,
    and known pain points. Call this as the very first tool in every conversation."""
    data = load_json(f"crm/leads/{lead_id}.json")
    if data is None:
        return {
            "found": False,
            "lead_id": lead_id,
            "note": "No prior CRM record. Collect company, team size, and pain points.",
        }
    return {"found": True, **data}
