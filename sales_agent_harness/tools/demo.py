"""Tool: book_demo — confirm a demo appointment and persist the booking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ._db import exists, load_json, write_json


class BookDemoArgs(BaseModel):
    lead_id: str = Field(description="CRM lead identifier, e.g. 'L123'.")
    slot_id: str = Field(
        description="Slot identifier from check_calendar, e.g. 'sg-tue-1000'."
    )
    attendee_email: str = Field(
        description="Prospect's confirmed email address for the calendar invite."
    )
    summary: str = Field(
        description="One-sentence context for the demo (pain point + goal)."
    )


@tool(args_schema=BookDemoArgs)
def book_demo(
    lead_id: str,
    slot_id: str,
    attendee_email: str,
    summary: str,
) -> dict[str, Any]:
    """Book a demo slot for a lead. Returns success=true and booking_id on success.
    Returns success=false if the slot is already taken or the slot_id is invalid.
    Only call after check_calendar confirmed the slot is available and the attendee
    email has been explicitly provided by the prospect."""
    # validate slot exists in calendar
    all_slots = load_json("calendar/slots.json")
    slot = next(
        (s for s in (all_slots or []) if s["slot_id"] == slot_id),
        None,
    )
    if slot is None:
        return {"success": False, "error": "invalid_slot_id", "slot_id": slot_id}

    booking_path = f"crm/demos/{slot_id}.json"
    if exists(booking_path):
        existing = load_json(booking_path) or {}
        return {
            "success": False,
            "error": "slot_already_booked",
            "slot_id": slot_id,
            "booked_by": existing.get("lead_id"),
        }

    booking_id = f"demo-{lead_id}-{slot_id}"
    booking = {
        "booking_id": booking_id,
        "lead_id": lead_id,
        "slot_id": slot_id,
        "slot_label": slot.get("label", slot_id),
        "attendee_email": attendee_email,
        "summary": summary,
        "status": "confirmed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(booking_path, booking)
    return {
        "success": True,
        "booking_id": booking_id,
        "slot_label": slot.get("label", slot_id),
        "attendee_email": attendee_email,
    }
