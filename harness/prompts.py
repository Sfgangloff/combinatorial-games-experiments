"""Prompts shown to the model. Kept separate so they can be tuned without touching the runner."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES = (REPO / "rules.md").read_text()


SYSTEM_PROMPT = f"""You are solving Slitherlink puzzles.

The rules:
{RULES}

You have ONLY MCP tools available — no shell, file, or web tools. Every action must go through an MCP tool call. The slitherlink-judge server is always available for fetching the puzzle and submitting solutions. Other servers (if present) provide tools for working through the puzzle.

When you finish, call mcp__slitherlink-judge__submit_solution with the full grid text in the same format as the puzzle but with the loop drawn in. The judge will tell you whether it is correct.

If you cannot make progress, say so explicitly and stop calling tools."""


def user_prompt(puzzle_id: str) -> str:
    return (
        f"Solve Slitherlink puzzle {puzzle_id!r}. "
        f"Start by calling mcp__slitherlink-judge__get_puzzle to fetch it. "
        f"Submit your solution when done."
    )
