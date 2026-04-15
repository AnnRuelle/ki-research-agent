"""Q&A harness: runs the Q&A agent against the real KB with a single question.

Produces tests/output/qa_answer.md for PL review. Reports token cost via
cost_tracker. Budget-capped via config.budget.max_usd_per_run.

Usage:
    python tests/run_qa.py
    python tests/run_qa.py "Welche Kantone setzen Azure ein?"
"""

from __future__ import annotations

import sys
from pathlib import Path

from agents import cost_tracker
from agents.config_schema import load_config
from agents.cost_tracker import BudgetExceededError
from agents.logging_config import setup_logging
from agents.qa import ask

OUTPUT_DIR = Path("tests/output")

DEFAULT_QUESTION = "Welche Kantone setzen auf Azure OpenAI und welche auf Open-Source-Stacks?"


def _print_cost_summary() -> None:
    total = cost_tracker.total()
    budget = cost_tracker.budget()
    budget_str = f" / ${budget:.2f} cap" if budget is not None else ""
    print(f"\nLLM cost this run: ${total:.4f}{budget_str}")
    for agent, cost in sorted(cost_tracker.by_agent().items(), key=lambda kv: -kv[1]):
        calls = cost_tracker.call_counts().get(agent, 0)
        print(f"  {agent:20s}  ${cost:.4f}  ({calls} calls)")


def run_qa(question: str) -> None:
    setup_logging(level="INFO")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    config = load_config()
    cost_tracker.reset(budget_usd=config.budget.max_usd_per_run)

    print(f"{'=' * 60}")
    print("Q&A Harness")
    print(f"Frage: {question}")
    if config.budget.max_usd_per_run is not None:
        print(f"Budget cap: ${config.budget.max_usd_per_run:.2f}")
    print(f"{'=' * 60}")

    try:
        answer = ask(question, output_dir=OUTPUT_DIR)
        print(f"\n{'-' * 60}")
        print("Antwort:")
        print(f"{'-' * 60}")
        print(answer)
        print(f"{'-' * 60}")
        print(f"\nAntwort gespeichert: {OUTPUT_DIR / 'qa_answer.md'}")
        print(f"Antwort-Laenge: {len(answer.split())} Woerter")
    except BudgetExceededError as e:
        print(f"\n⛔ Pipeline stopped: {e}")
    finally:
        _print_cost_summary()


def main() -> None:
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUESTION
    run_qa(question)


if __name__ == "__main__":
    main()
