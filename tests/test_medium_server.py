"""
In-process test of slitherlink-medium server tools.

Imports the server module and calls the FastMCP-registered functions through
their underlying Python implementations to verify wiring + state lifecycle.
"""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SERVER_PATH = REPO / "servers" / "slitherlink-medium" / "server.py"
PUZZLE_PATH = REPO / "legacy" / "slitherlink-batch-experiment" / "grid_step_0.txt"


def _import_server():
    spec = importlib.util.spec_from_file_location("medium_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def main():
    server = _import_server()
    mcp = server.mcp

    tools = await mcp.list_tools()
    tools = {t.name: t for t in tools}
    expected = {
        "load", "render", "apply_edge", "forced_moves",
        "check_consistency", "endpoints", "solved", "snapshot", "restore",
    }
    actual = set(tools.keys())
    assert expected <= actual, f"missing tools: {expected - actual}"
    print(f"tools registered: {sorted(actual)}")

    # Use the underlying functions directly (not via MCP transport).
    grid_text = PUZZLE_PATH.read_text()
    loaded = server.load(grid_text=grid_text)
    handle = loaded["handle"]
    print(f"loaded handle={handle} summary={loaded['summary']}")

    forced = server.forced_moves(handle=handle)
    assert forced["contradiction"] is None
    print(f"forced_moves: {len(forced['changes'])} changes "
          f"(expect 4 from the 0-cell)")

    snap = server.snapshot(handle=handle, label="start")
    snap_id = snap["snap_id"]
    print(f"snapshot: {snap_id}")

    applied = server.apply_edge(
        handle=handle, edge_type="H", row=0, col=0, value="line"
    )
    assert applied["contradiction"] is None
    print(f"apply_edge H[0][0]=line propagated {len(applied['changes'])} changes")

    issues = server.check_consistency(handle=handle)
    assert issues["issues"] == [], issues
    print("consistency clean")

    eps = server.endpoints(handle=handle)
    print(f"endpoints: {eps['dots']}")

    rendered = server.render(handle=handle)
    print("render:")
    print(rendered["ascii"])

    restored = server.restore(handle=handle, snap_id=snap_id)
    print(f"restore ok={restored['ok']}")

    bad = server.apply_edge(
        handle=handle, edge_type="H", row=3, col=2, value="line"
    )
    assert bad["contradiction"] is not None
    print(f"contradiction-on-zero-cell OK: {bad['contradiction']}")

    print("\nAll medium-server tests passed.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
