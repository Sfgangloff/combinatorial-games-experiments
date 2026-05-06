"""Smoke test for slitherlink-judge."""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SERVER_PATH = REPO / "servers" / "slitherlink-judge" / "server.py"


def _import_server():
    spec = importlib.util.spec_from_file_location("judge_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# A valid solution to puzzle_001 (5x5). Worked out by hand to seed the test.
# Loop visualized:
#   +---+---+   +   +   +
#   | 3   .   .   2   .|
#   +   +---+   +---+   +
#   | .   2 | 1 | 3   3
#   +---+   +   +   +---+
#       . | .   2   . | 2
#   +   +---+   +   +   +
#       .   . | 0   .   2
#   +   +   +   +   +   +
#   ...
# Rather than commit to a specific solution by hand, the test only verifies
# that submit_solution rejects the empty grid (which is parsable but unsolved)
# and the "tampered" grid (numbers changed). A real solution test will be
# added once a puzzle is actually solved end-to-end.


async def main():
    server = _import_server()
    tools = await server.mcp.list_tools()
    print(f"tools: {sorted(t.name for t in tools)}")

    listed = server.list_puzzles()
    assert listed["puzzles"], listed
    print(f"puzzles: {[p['id'] for p in listed['puzzles']]}")

    p = server.get_puzzle(puzzle_id="puzzle_001")
    print(f"puzzle_001 first line: {p['grid_text'].splitlines()[0]!r}")

    # Empty grid should parse but fail is_solved.
    result = server.submit_solution(puzzle_id="puzzle_001", grid_text=p["grid_text"])
    assert result["correct"] is False
    print(f"empty submission rejected: {result['reason']}")

    # Tampered grid (change a number).
    tampered = p["grid_text"].replace("3", "1", 1)
    result = server.submit_solution(puzzle_id="puzzle_001", grid_text=tampered)
    assert result["correct"] is False
    print(f"tampered submission rejected: {result['reason'][:60]}...")

    print("\nAll judge-server tests passed.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
