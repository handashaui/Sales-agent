"""Sales agent tools — all six exported as a list for create_react_agent."""

from .calendar import check_calendar
from .crm import write_crm_note
from .demo import book_demo
from .handoff import handoff_to_human
from .knowledge import search_knowledge_base
from .lead import get_lead_context

all_tools = [
    get_lead_context,
    search_knowledge_base,
    check_calendar,
    book_demo,
    write_crm_note,
    handoff_to_human,
]

__all__ = [
    "all_tools",
    "get_lead_context",
    "search_knowledge_base",
    "check_calendar",
    "book_demo",
    "write_crm_note",
    "handoff_to_human",
]
