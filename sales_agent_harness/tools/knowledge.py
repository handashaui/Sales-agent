"""Tool: search_knowledge_base — keyword search over product/policy KB."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ._db import load_json


class SearchKBArgs(BaseModel):
    query: str = Field(
        description=(
            "Natural-language query. Use when the user asks about pricing, ROI, "
            "product capabilities, customer references, or any claim you cannot verify."
        )
    )


@tool(args_schema=SearchKBArgs)
def search_knowledge_base(query: str) -> dict[str, Any]:
    """Search the product and policy knowledge base. Returns matching entries with
    their content. If pricing, ROI, or reference entries come back, follow their
    policy guidance — do NOT fabricate numbers or named customers."""
    entries = load_json("kb/products.json")
    if not isinstance(entries, list):
        return {"query": query, "results": []}

    q = query.lower()
    scored: list[tuple[int, dict]] = []
    for entry in entries:
        hits = sum(1 for tag in entry.get("tags", []) if tag.lower() in q)
        # also match on title words
        hits += sum(1 for word in entry.get("title", "").lower().split() if word in q)
        if hits > 0:
            scored.append((hits, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_k = [e for _, e in scored[:3]]

    if not top_k:
        # fall back: return the general overview so the agent always gets something
        overview = next(
            (e for e in entries if e.get("id") == "product_overview"), None
        )
        top_k = [overview] if overview else []

    return {
        "query": query,
        "results": [{"title": e["title"], "content": e["content"]} for e in top_k],
    }
