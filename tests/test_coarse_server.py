"""Smoke test for slitherlink-coarse."""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SERVER_PATH = REPO / "servers" / "slitherlink-coarse" / "server.py"
PUZZLE_PATH = REPO / "legacy" / "slitherlink-batch-experiment" / "grid_step_0.txt"


def _import_server():
    spec = importlib.util.spec_from_file_location("coarse_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def main():
    server = _import_server()
    tools = await server.mcp.list_tools()
    names = sorted(t.name for t in tools)
    print(f"tools registered ({len(names)}): {names}")
    expected = {"load", "state", "suggest_next_move", "apply_move",
                "check_consistency", "solved"}
    assert expected <= set(names), f"missing: {expected - set(names)}"

    h = server.load(grid_text=PUZZLE_PATH.read_text())["handle"]

    # On a fresh puzzle, the 0-cell forces 4 blocks. suggest_next_move
    # should return a 'forced' move first.
    sug = server.suggest_next_move(handle=h)
    print(f"first suggestion: {sug}")
    assert sug["method"] == "forced"
    assert sug["move"]["value"] == "blocked"

    # Apply the suggested move.
    m = sug["move"]
    applied = server.apply_move(
        handle=h, edge_type=m["edge_type"], row=m["row"],
        col=m["col"], value=m["value"],
    )
    print(f"applied → {len(applied['changes'])} changes")

    # Drain forced moves loop.
    forced_count = 0
    for _ in range(50):
        sug = server.suggest_next_move(handle=h)
        if sug["method"] != "forced" or sug["move"] is None:
            break
        m = sug["move"]
        server.apply_move(
            handle=h, edge_type=m["edge_type"], row=m["row"],
            col=m["col"], value=m["value"],
        )
        forced_count += 1
    print(f"after draining forced: {forced_count} more applied; method={sug['method']}")

    # Try a lookahead suggestion.
    if sug["method"] == "stuck":
        # may legitimately be stuck on this puzzle without further work
        print("coarse stuck — that's a valid outcome on a hard puzzle")
    else:
        print(f"lookahead found: {sug}")

    issues = server.check_consistency(handle=h)["issues"]
    assert issues == [], issues

    print("\nAll coarse-server tests passed.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
