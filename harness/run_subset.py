"""
Run a subset of conditions for a single puzzle.

CLI:
    python -m harness.run_subset puzzle_002 fine medium coarse [--meta] [--max-turns 200]
"""
from __future__ import annotations

import argparse
import asyncio
import time

from harness.conditions import Condition
from harness.run import run_one
from harness.run_matrix import _format_row


async def main(args: argparse.Namespace) -> None:
    conditions = [Condition(toolset=t, meta=args.meta) for t in args.toolsets]
    print(f"Running {len(conditions)} conditions on {args.puzzle_id}: "
          f"{[c.name for c in conditions]}\n")
    rows: list[str] = []
    started = time.time()
    for cond in conditions:
        print(f"[{args.puzzle_id} | {cond.name}] starting...")
        record = await run_one(
            args.puzzle_id, cond,
            max_turns=args.max_turns, model=args.model, log=False,
        )
        row = _format_row(args.puzzle_id, cond, record)
        rows.append(row)
        print(row + "\n")
    print("\n" + "=" * 70)
    print("SUBSET SUMMARY")
    print("=" * 70)
    for r in rows:
        print(r)
    print(f"\nTotal wall time: {(time.time() - started) / 60:.1f} min")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("puzzle_id")
    p.add_argument("toolsets", nargs="+", choices=["none", "fine", "medium", "coarse", "scratchpad"])
    p.add_argument("--meta", action="store_true")
    p.add_argument("--max-turns", type=int, default=200)
    p.add_argument("--model", default=None)
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(main(_parse_args()))
