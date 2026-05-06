"""
Run the 8-condition matrix for one or more puzzles.

CLI:
    python -m harness.run_matrix puzzle_001 [puzzle_002 ...] [--max-turns 35]
"""
from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from harness.conditions import ALL_CONDITIONS, Condition
from harness.run import run_one


def _format_row(puzzle_id: str, condition: Condition, record: dict) -> str:
    o = record["outcome"]
    solved = "Y" if o["solved"] else "."
    err = "E" if record["error"] else " "
    elapsed = record["elapsed_seconds"]
    cost = None
    for msg in record["messages"]:
        if msg.get("role") == "result":
            cost = msg.get("total_cost_usd")
    cost_str = f"${cost:.2f}" if cost is not None else "-"
    return (
        f"  {puzzle_id:<12} {condition.toolset:<7} "
        f"meta={'on ' if condition.meta else 'off'} "
        f"solved={solved} err={err} "
        f"calls={o['tool_call_count']:>3} "
        f"errs={o['tool_errors']:>2} "
        f"time={elapsed:>5.1f}s "
        f"cost={cost_str:>6}"
    )


async def main(args: argparse.Namespace) -> None:
    print(f"Running matrix: {len(args.puzzle_ids)} puzzles x "
          f"{len(ALL_CONDITIONS)} conditions = "
          f"{len(args.puzzle_ids) * len(ALL_CONDITIONS)} runs\n")

    rows: list[str] = []
    started = time.time()

    for puzzle_id in args.puzzle_ids:
        for condition in ALL_CONDITIONS:
            print(f"[{puzzle_id} | {condition.name}] starting...")
            record = await run_one(
                puzzle_id, condition,
                max_turns=args.max_turns,
                model=args.model,
                log=False,
            )
            row = _format_row(puzzle_id, condition, record)
            rows.append(row)
            print(row + "\n")

    total = time.time() - started
    print("\n" + "=" * 70)
    print("MATRIX SUMMARY")
    print("=" * 70)
    for r in rows:
        print(r)
    print(f"\nTotal wall time: {total / 60:.1f} min")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("puzzle_ids", nargs="+")
    p.add_argument("--max-turns", type=int, default=35)
    p.add_argument("--model", default=None)
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(main(_parse_args()))
