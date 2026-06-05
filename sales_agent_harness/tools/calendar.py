"""Tool: check_calendar — list available demo slots filtered by timezone."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ._db import load_json

_TIMEZONE_ALIASES: dict[str, str] = {
    "cst": "Asia/Shanghai",
    "china": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "beijing": "Asia/Shanghai",
    "sgt": "Asia/Singapore",
    "singapore": "Asia/Singapore",
    "asia/shanghai": "Asia/Shanghai",
    "asia/singapore": "Asia/Singapore",
}


class CheckCalendarArgs(BaseModel):
    timezone: str = Field(
        description=(
            "Prospect's timezone. Accepts IANA names ('Asia/Shanghai', 'Asia/Singapore') "
            "or aliases ('CST', 'SGT', 'Shanghai', 'Singapore'). Default: 'Asia/Shanghai'."
        )
    )
    duration_minutes: int = Field(
        default=30,
        description="Requested demo duration in minutes. Typically 30.",
    )


@tool(args_schema=CheckCalendarArgs)
def check_calendar(timezone: str, duration_minutes: int = 30) -> dict[str, Any]:
    """Return available demo slots for the given timezone. Call before book_demo to
    pick a valid slot_id. Returns slot_id, label, and timezone for each open slot."""
    canonical = _TIMEZONE_ALIASES.get(timezone.lower(), timezone)
    all_slots = load_json("calendar/slots.json")
    if not isinstance(all_slots, list):
        return {"timezone": canonical, "duration_minutes": duration_minutes, "available_slots": []}

    available = [
        {"slot_id": s["slot_id"], "label": s["label"], "timezone": s["timezone"]}
        for s in all_slots
        if s.get("available") and s.get("timezone") == canonical
        and s.get("duration_minutes", 30) <= duration_minutes
    ]
    return {
        "timezone": canonical,
        "duration_minutes": duration_minutes,
        "available_slots": available,
    }
