"""Mock tools for the sales agent harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


ToolFn = Callable[..., dict[str, Any]]


@dataclass
class MockToolRuntime:
    """In-memory tool runtime with enough state for tests and demos."""

    crm_notes: list[dict[str, Any]] = field(default_factory=list)
    booked_demos: list[dict[str, Any]] = field(default_factory=list)
    handoffs: list[dict[str, Any]] = field(default_factory=list)

    def get_lead_context(self, lead_id: str) -> dict[str, Any]:
        seeded = {
            "L123": {
                "source": "website",
                "industry": "manufacturing",
                "region": "APAC",
                "owner": "sales-apac@example.com",
            },
            "L-DEMO": {
                "source": "event",
                "industry": "software",
                "region": "Singapore",
                "owner": "demo-team@example.com",
            },
            "L-LOW": {
                "source": "newsletter",
                "industry": "unknown",
                "region": "unknown",
                "owner": "queue@example.com",
            },
        }
        return {
            "lead_id": lead_id,
            **seeded.get(
                lead_id,
                {
                    "source": "inbound",
                    "industry": "unknown",
                    "region": "unknown",
                    "owner": "sales-queue@example.com",
                },
            ),
        }

    def search_knowledge_base(self, query: str) -> dict[str, Any]:
        query_lower = query.lower()
        entries = []
        if any(term in query_lower for term in ["price", "价格", "报价", "pricing"]):
            entries.append(
                {
                    "title": "Pricing policy",
                    "summary": (
                        "Public pricing is not committed by the agent. Exact "
                        "pricing depends on scope and must be handled by sales."
                    ),
                }
            )
        if any(term in query_lower for term in ["case", "案例", "customer", "客户"]):
            entries.append(
                {
                    "title": "Reference policy",
                    "summary": (
                        "Customer references require approval. The agent may "
                        "describe general use cases, not named customer claims."
                    ),
                }
            )
        if any(term in query_lower for term in ["manufactur", "制造"]):
            entries.append(
                {
                    "title": "Manufacturing lead follow-up",
                    "summary": (
                        "Common pains include slow lead response, missed follow-up, "
                        "CRM hygiene, and prioritization across sales reps."
                    ),
                }
            )
        if not entries:
            entries.append(
                {
                    "title": "Sales assistant scope",
                    "summary": (
                        "The assistant can qualify leads, suggest next steps, "
                        "book demos, and prepare CRM notes."
                    ),
                }
            )
        return {"query": query, "results": entries}

    def check_calendar(
        self, timezone_name: str = "Asia/Shanghai", duration_minutes: int = 30
    ) -> dict[str, Any]:
        slots_by_timezone = {
            "Asia/Singapore": [
                {"slot_id": "sg-tue-1000", "label": "周二 10:00 SGT"},
                {"slot_id": "sg-wed-1500", "label": "周三 15:00 SGT"},
            ],
            "Asia/Shanghai": [
                {"slot_id": "cn-tue-1000", "label": "周二 10:00 CST"},
                {"slot_id": "cn-wed-1500", "label": "周三 15:00 CST"},
            ],
        }
        return {
            "timezone": timezone_name,
            "duration_minutes": duration_minutes,
            "available_slots": slots_by_timezone.get(
                timezone_name, slots_by_timezone["Asia/Shanghai"]
            ),
        }

    def book_demo(
        self,
        lead_id: str,
        slot_id: str,
        email: str,
        timezone_name: str = "Asia/Shanghai",
    ) -> dict[str, Any]:
        booking = {
            "booking_id": f"demo-{len(self.booked_demos) + 1:03d}",
            "lead_id": lead_id,
            "slot_id": slot_id,
            "email": email,
            "timezone": timezone_name,
            "status": "booked",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.booked_demos.append(booking)
        return booking

    def write_crm_note(
        self,
        lead_id: str,
        summary: str,
        qualification_level: str,
        next_action: str,
    ) -> dict[str, Any]:
        note = {
            "note_id": f"crm-{len(self.crm_notes) + 1:03d}",
            "lead_id": lead_id,
            "summary": summary,
            "qualification_level": qualification_level,
            "next_action": next_action,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.crm_notes.append(note)
        return note

    def handoff_to_human(
        self, lead_id: str, reason: str, priority: str = "normal"
    ) -> dict[str, Any]:
        handoff = {
            "handoff_id": f"handoff-{len(self.handoffs) + 1:03d}",
            "lead_id": lead_id,
            "reason": reason,
            "priority": priority,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.handoffs.append(handoff)
        return handoff

    def registry(self) -> dict[str, ToolFn]:
        return {
            "get_lead_context": self.get_lead_context,
            "search_knowledge_base": self.search_knowledge_base,
            "check_calendar": self.check_calendar,
            "book_demo": self.book_demo,
            "write_crm_note": self.write_crm_note,
            "handoff_to_human": self.handoff_to_human,
        }
