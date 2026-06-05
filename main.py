"""Compatibility wrapper for the package CLI."""

from __future__ import annotations

from sales_agent_harness.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
