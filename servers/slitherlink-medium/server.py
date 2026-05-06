"""
slitherlink-medium MCP server.

Exposes ~9 tools that bundle one-step local inference. The model still picks
moves and strategy; the server does the bookkeeping (counting edges around
dots and cells) and propagates well-known local rules to a fixed point.

Run as a stdio MCP server:
    python servers/slitherlink-medium/server.py
"""
from __future__ import annotations

import uuid

from fastmcp import FastMCP

from core import (
    SlitherlinkState,
    apply_edge as core_apply_edge,
    check_consistency as core_check_consistency,
    endpoints as core_endpoints,
    forced_moves as core_forced_moves,
    is_solved as core_is_solved,
    load_from_text,
    render as core_render,
)

mcp = FastMCP("slitherlink-medium")

_states: dict[str, SlitherlinkState] = {}
_snapshots: dict[str, dict[str, SlitherlinkState]] = {}


def _get(handle: str) -> SlitherlinkState:
    state = _states.get(handle)
    if state is None:
        raise ValueError(f"unknown handle: {handle!r}. Call load() first.")
    return state


def _summary(state: SlitherlinkState) -> dict:
    """Quick numeric summary, useful right after load and after big moves."""
    from core.state import EdgeState

    cells_by_value: dict[int, list[list[int]]] = {}
    for (r, c), n in state.cells.items():
        cells_by_value.setdefault(n, []).append([r, c])
    line_h = sum(1 for s in state.h_edges.values() if s == EdgeState.LINE)
    line_v = sum(1 for s in state.v_edges.values() if s == EdgeState.LINE)
    blocked_h = sum(1 for s in state.h_edges.values() if s == EdgeState.BLOCKED)
    blocked_v = sum(1 for s in state.v_edges.values() if s == EdgeState.BLOCKED)
    return {
        "num_rows": state.num_rows,
        "num_cols": state.num_cols,
        "cells_by_value": cells_by_value,
        "line_edges": line_h + line_v,
        "blocked_edges": blocked_h + blocked_v,
        "endpoints": [[r, c] for (r, c) in core_endpoints(state)],
    }


@mcp.tool
def load(grid_text: str) -> dict:
    """
    Parse a Slitherlink puzzle in textual format and return a state handle.

    The grid uses '+' for dots, '.' for cells without numbers, and '0'-'3' for
    numbered cells. Existing edges may be drawn with '---' (horizontal lines)
    or '|' (vertical lines), but new puzzles typically have none.

    Returns:
        handle: opaque string identifying this puzzle's state across calls.
        summary: dimensions, cell-numbers grouped by value, edge counts, endpoints.
    """
    state = load_from_text(grid_text)
    handle = uuid.uuid4().hex[:8]
    _states[handle] = state
    _snapshots[handle] = {}
    return {"handle": handle, "summary": _summary(state)}


@mcp.tool
def render(handle: str, show_blocked: bool = True) -> dict:
    """
    Return the current state as ASCII text. 'x' marks blocked edges when
    show_blocked=True; otherwise blocked and unknown edges look the same.
    """
    state = _get(handle)
    return {"ascii": core_render(state, show_blocked=show_blocked)}


@mcp.tool
def apply_edge(handle: str, edge_type: str, row: int, col: int, value: str) -> dict:
    """
    Set a single edge to LINE or BLOCKED, then propagate local rules to a
    fixed point. Local rules used:
      - cells with N already-line edges block all other sides;
      - cells needing exactly K more edges and having only K unknown sides force them;
      - dots with 2 line edges block their other sides;
      - dots with 1 line edge and only 1 unknown side force that side to line;
      - dots with 0 line edges and only 1 unknown side block it.

    Args:
        edge_type: 'H' or 'V'.
        row, col: see edge indexing in core/state.py.
        value: 'line' or 'blocked'.

    Returns:
        changes: list of {edge, edge_type, row, col, new_state, reason}.
        contradiction: null on success, or a string explaining the conflict.
                       (state is left as-is on contradiction so it can be inspected.)
    """
    state = _get(handle)
    result = core_apply_edge(state, edge_type, row, col, value)
    return result.as_dict()


@mcp.tool
def forced_moves(handle: str) -> dict:
    """
    Return all edges that local rules currently force, with reasons. Does NOT
    mutate the state — useful to preview what apply_edge would cascade into.
    """
    state = _get(handle)
    result = core_forced_moves(state)
    return result.as_dict()


@mcp.tool
def check_consistency(handle: str) -> dict:
    """
    Return a list of consistency violations: empty list means no contradiction
    is detectable by local rules. Detects over-/under-satisfied cells, dots
    with too many line edges, multiple open path components, premature loop
    closure with cells still unsatisfied.
    """
    state = _get(handle)
    return {"issues": core_check_consistency(state)}


@mcp.tool
def endpoints(handle: str) -> dict:
    """
    Return dots that currently have exactly 1 line edge — the endpoints of
    the open path. A solved puzzle has zero endpoints (closed loop).
    """
    state = _get(handle)
    return {"dots": [[r, c] for (r, c) in core_endpoints(state)]}


@mcp.tool
def solved(handle: str) -> dict:
    """
    Check whether the puzzle is fully solved. Returns {solved: bool, reason: str}.
    """
    state = _get(handle)
    ok, reason = core_is_solved(state)
    return {"solved": ok, "reason": reason}


@mcp.tool
def snapshot(handle: str, label: str | None = None) -> dict:
    """
    Save a copy of the current state under a snapshot id, so it can be
    restored later. Useful for trying a tentative move and undoing if it fails.

    Args:
        label: optional human-readable label (the snap_id is auto-generated).
    """
    state = _get(handle)
    snap_id = uuid.uuid4().hex[:6]
    if label:
        snap_id = f"{label}-{snap_id}"
    _snapshots[handle][snap_id] = state.clone()
    return {"snap_id": snap_id, "snapshots": list(_snapshots[handle].keys())}


@mcp.tool
def restore(handle: str, snap_id: str) -> dict:
    """Restore the state from a previously saved snapshot."""
    state = _get(handle)
    snaps = _snapshots.get(handle, {})
    if snap_id not in snaps:
        raise ValueError(
            f"unknown snap_id {snap_id!r}; available: {list(snaps.keys())}"
        )
    _states[handle] = snaps[snap_id].clone()
    return {"ok": True, "summary": _summary(_states[handle])}


if __name__ == "__main__":
    mcp.run()
