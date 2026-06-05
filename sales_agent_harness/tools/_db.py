"""File-based DB helpers for the sales agent tool layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# sales_agent_harness/tools/_db.py → 3 parents up → repo root → data/
DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _data(rel: str) -> Path:
    return DATA_DIR / rel


def load_json(rel_path: str) -> dict[str, Any] | list[Any] | None:
    path = _data(rel_path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def append_json(rel_path: str, record: dict[str, Any]) -> None:
    path = _data(rel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    records: list[Any] = []
    if path.exists():
        records = json.loads(path.read_text(encoding="utf-8"))
    records.append(record)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def write_json(rel_path: str, data: dict[str, Any]) -> None:
    path = _data(rel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def exists(rel_path: str) -> bool:
    return _data(rel_path).exists()
