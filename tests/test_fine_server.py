"""Smoke test for slitherlink-fine. Drives @mcp.tool functions in-process."""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SERVER_PATH = REPO / "servers" / "slitherlink-fine" / "server.py"
PUZZLE_PATH = REPO / "legacy" / "slitherlink-batch-experiment" / "grid_step_0.txt"


def _import_server():
    spec = importlib.util.spec_from_file_location("fine_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def main():
    server = _import_server()
    tools = await server.mcp.list_tools()
    names = sorted(t.name for t in tools)
    print(f"tools registered ({len(names)}): {names}")
    expected = {
        "load", "render", "dimensions", "get_cell_number", "list_numbered_cells",
        "get_edge", "set_edge", "reset_edge", "count_edges_around_cell",
        "count_edges_at_dot", "list_edges_around_cell", "list_edges_at_dot",
        "list_endpoints", "list_full_dots", "snapshot", "restore", "solved",
    }
    assert expected <= set(names), f"missing: {expected - set(names)}"

    grid = PUZZLE_PATH.read_text()
    h = server.load(grid_text=grid)["handle"]

    dims = server.dimensions(handle=h)
    assert dims == {"num_rows": 5, "num_cols": 5}

    n = server.get_cell_number(handle=h, row=3, col=2)["number"]
    assert n == 0, f"expected (3,2)=0, got {n}"

    counts = server.count_edges_around_cell(handle=h, row=0, col=0)
    assert counts == {"unknown": 4, "line": 0, "blocked": 0}

    server.set_edge(handle=h, edge_type="H", row=0, col=0, value="line")
    state = server.get_edge(handle=h, edge_type="H", row=0, col=0)["state"]
    assert state == "line"

    counts2 = server.count_edges_around_cell(handle=h, row=0, col=0)
    assert counts2 == {"unknown": 3, "line": 1, "blocked": 0}, counts2

    eps = server.list_endpoints(handle=h)["dots"]
    assert len(eps) == 2, eps  # H[0][0] gives 2 degree-1 dots

    snap = server.snapshot(handle=h, label="t1")["snap_id"]
    server.set_edge(handle=h, edge_type="H", row=0, col=1, value="line")
    server.restore(handle=h, snap_id=snap)
    after = server.get_edge(handle=h, edge_type="H", row=0, col=1)["state"]
    assert after == "unknown", after

    overwrite_caught = False
    try:
        server.set_edge(handle=h, edge_type="H", row=0, col=0, value="blocked")
    except ValueError as e:
        overwrite_caught = True
        print(f"overwrite rejected as expected: {e}")
    assert overwrite_caught

    server.reset_edge(handle=h, edge_type="H", row=0, col=0)
    state = server.get_edge(handle=h, edge_type="H", row=0, col=0)["state"]
    assert state == "unknown"

    print("\nAll fine-server tests passed.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
