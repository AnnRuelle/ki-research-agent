"""Per-run LLM cost tracking with optional budget cap.

Tracks cumulative cost per agent across a pipeline run. When a budget is set
via `reset(budget_usd=N)`, any track() call that pushes the total past N
raises BudgetExceededError — callers stop cleanly instead of running up bills.

Usage at pipeline entry:
    cost_tracker.reset(budget_usd=5.0)
    ...
    try:
        run_pipeline()
    except BudgetExceededError as e:
        logger.error("Stopping: %s", e)
    finally:
        logger.info("Cost summary: %s (total $%.2f)",
                    cost_tracker.by_agent(), cost_tracker.total())
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_totals: dict[str, float] = defaultdict(float)
_calls: dict[str, int] = defaultdict(int)
_budget_usd: float | None = None


class BudgetExceededError(Exception):
    """Raised when cumulative cost exceeds the configured budget."""

    def __init__(self, spent: float, budget: float) -> None:
        super().__init__(f"Budget exceeded: spent ${spent:.4f} > cap ${budget:.2f}")
        self.spent = spent
        self.budget = budget


def reset(budget_usd: float | None = None) -> None:
    """Clear counters and set (or clear) the per-run budget cap."""
    global _budget_usd
    with _lock:
        _totals.clear()
        _calls.clear()
        _budget_usd = budget_usd
    if budget_usd is not None:
        logger.info("cost_tracker: reset with budget cap $%.2f", budget_usd)


def track(agent: str, cost_usd: float) -> None:
    """Record one LLM call. Raises BudgetExceededError if over budget."""
    with _lock:
        _totals[agent] += cost_usd
        _calls[agent] += 1
        total_spent = sum(_totals.values())
        budget = _budget_usd
    if budget is not None and total_spent > budget:
        raise BudgetExceededError(total_spent, budget)


def total() -> float:
    """Cumulative cost across all agents in this run."""
    with _lock:
        return sum(_totals.values())


def by_agent() -> dict[str, float]:
    """Cost broken down by agent."""
    with _lock:
        return dict(_totals)


def call_counts() -> dict[str, int]:
    """Number of LLM calls per agent."""
    with _lock:
        return dict(_calls)


def budget() -> float | None:
    """Currently configured budget cap, if any."""
    return _budget_usd
