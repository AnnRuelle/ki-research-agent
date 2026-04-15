"""Unit tests for agents.cost_tracker."""

from __future__ import annotations

import pytest

from agents import cost_tracker
from agents.cost_tracker import BudgetExceededError

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_tracker() -> None:
    """Reset tracker state before each test."""
    cost_tracker.reset()


class TestReset:
    def test_clears_totals_and_calls(self) -> None:
        cost_tracker.track("researcher", 0.5)
        cost_tracker.reset()
        assert cost_tracker.total() == 0.0
        assert cost_tracker.by_agent() == {}
        assert cost_tracker.call_counts() == {}

    def test_sets_budget(self) -> None:
        cost_tracker.reset(budget_usd=2.5)
        assert cost_tracker.budget() == 2.5

    def test_clears_budget_when_none(self) -> None:
        cost_tracker.reset(budget_usd=1.0)
        cost_tracker.reset()
        assert cost_tracker.budget() is None


class TestTrack:
    def test_accumulates_per_agent(self) -> None:
        cost_tracker.track("researcher", 0.10)
        cost_tracker.track("researcher", 0.20)
        cost_tracker.track("writer", 0.05)
        assert cost_tracker.by_agent() == {"researcher": pytest.approx(0.30), "writer": pytest.approx(0.05)}

    def test_counts_calls(self) -> None:
        cost_tracker.track("researcher", 0.01)
        cost_tracker.track("researcher", 0.01)
        cost_tracker.track("writer", 0.01)
        assert cost_tracker.call_counts() == {"researcher": 2, "writer": 1}

    def test_total_sums_all_agents(self) -> None:
        cost_tracker.track("a", 0.1)
        cost_tracker.track("b", 0.2)
        cost_tracker.track("c", 0.3)
        assert cost_tracker.total() == pytest.approx(0.6)


class TestBudget:
    def test_no_budget_never_raises(self) -> None:
        cost_tracker.reset()
        cost_tracker.track("researcher", 999.0)
        assert cost_tracker.total() == 999.0

    def test_under_budget_allows(self) -> None:
        cost_tracker.reset(budget_usd=1.0)
        cost_tracker.track("researcher", 0.5)
        cost_tracker.track("writer", 0.4)
        assert cost_tracker.total() == pytest.approx(0.9)

    def test_over_budget_raises(self) -> None:
        cost_tracker.reset(budget_usd=1.0)
        cost_tracker.track("researcher", 0.6)
        with pytest.raises(BudgetExceededError) as exc_info:
            cost_tracker.track("writer", 0.5)
        assert exc_info.value.spent == pytest.approx(1.1)
        assert exc_info.value.budget == 1.0

    def test_exact_budget_does_not_raise(self) -> None:
        cost_tracker.reset(budget_usd=1.0)
        cost_tracker.track("researcher", 1.0)

    def test_records_cost_before_raising(self) -> None:
        cost_tracker.reset(budget_usd=1.0)
        cost_tracker.track("researcher", 0.8)
        with pytest.raises(BudgetExceededError):
            cost_tracker.track("researcher", 0.5)
        assert cost_tracker.total() == pytest.approx(1.3)


class TestBudgetExceededError:
    def test_message_format(self) -> None:
        err = BudgetExceededError(5.1234, 5.0)
        assert "5.1234" in str(err)
        assert "5.00" in str(err)

    def test_attributes(self) -> None:
        err = BudgetExceededError(5.1234, 5.0)
        assert err.spent == 5.1234
        assert err.budget == 5.0
