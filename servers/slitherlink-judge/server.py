"""
slitherlink-judge MCP server.

Always present in every experimental condition. Provides:
  - list_puzzles(): catalog of available puzzles with metadata
  - get_puzzle(id): the raw puzzle text for a given id
  - submit_solution(puzzle_id, grid_text): validates a submission

Validation uses core.is_solved on the parsed submission and additionally checks
that the solver hasn't changed any cell numbers (i.e. they match the original
puzzle). Slitherlink solutions are unique on well-formed puzzles, so a state
that satisfies all constraints IS the solution.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastmcp import FastMCP

from core import is_solved, load_from_text

mcp = FastMCP("slitherlink-judge")

PUZZLES_DIR = Path(__file__).resolve().parent.parent.parent / "puzzles"
MANIFEST_PATH = PUZZLES_DIR / "manifest.json"


def _load_manifest() -> list[dict]:
    return json.loads(MANIFEST_PATH.read_text())["puzzles"]


def _puzzle_text(puzzle_id: str) -> str:
    for entry in _load_manifest():
        if entry["id"] == puzzle_id:
            return (PUZZLES_DIR / entry["file"]).read_text()
    raise ValueError(f"unknown puzzle id: {puzzle_id!r}")


@mcp.tool
def list_puzzles() -> dict:
    """List all available puzzles with id, size, difficulty, source."""
    return {"puzzles": _load_manifest()}


@mcp.tool
def get_puzzle(puzzle_id: str) -> dict:
    """Return the raw puzzle text for a given id."""
    return {"puzzle_id": puzzle_id, "grid_text": _puzzle_text(puzzle_id)}


@mcp.tool
def submit_solution(puzzle_id: str, grid_text: str) -> dict:
    """
    Validate a submission against the original puzzle.

    Checks:
      1. Submission parses as a Slitherlink grid.
      2. Cell numbers match the original puzzle (no tampering).
      3. is_solved on the submission returns true (constraints satisfied,
         single closed loop).

    Returns:
        correct: bool
        reason: short explanation
    """
    original = load_from_text(_puzzle_text(puzzle_id))
    try:
        submitted = load_from_text(grid_text)
    except Exception as e:
        return {"correct": False, "reason": f"could not parse submission: {e}"}

    if (submitted.num_rows, submitted.num_cols) != (original.num_rows, original.num_cols):
        return {
            "correct": False,
            "reason": (
                f"dimensions changed: original {original.num_rows}x{original.num_cols}, "
                f"submitted {submitted.num_rows}x{submitted.num_cols}"
            ),
        }
    if submitted.cells != original.cells:
        diff_orig = set(original.cells.items()) - set(submitted.cells.items())
        diff_sub = set(submitted.cells.items()) - set(original.cells.items())
        return {
            "correct": False,
            "reason": (
                f"cell numbers changed; missing/changed in submission: {diff_orig}, "
                f"unexpected in submission: {diff_sub}"
            ),
        }

    ok, reason = is_solved(submitted)
    return {"correct": ok, "reason": reason}


if __name__ == "__main__":
    mcp.run()
