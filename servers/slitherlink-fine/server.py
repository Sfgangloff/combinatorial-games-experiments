"""
slitherlink-fine MCP server.

Many small tools that read/write state but do NO inference. The model is
responsible for all deductions; the server just stops it from having to
re-render the grid or recount edges in its head.

Run as a stdio MCP server:
    python servers/slitherlink-fine/server.py
"""
from __future__ import annotations

import uuid

from fastmcp import FastMCP

from core import (
    EdgeState,
    SlitherlinkState,
    is_solved as core_is_solved,
    load_from_text,
    render as core_render,
)

mcp = FastMCP("slitherlink-fine")

_states: dict[str, SlitherlinkState] = {}
_snapshots: dict[str, dict[str, SlitherlinkState]] = {}


def _get(handle: str) -> SlitherlinkState:
    state = _states.get(handle)
    if state is None:
        raise ValueError(f"unknown handle: {handle!r}. Call load() first.")
    return state


def _edge_dict(et: str, r: int, c: int, s: EdgeState) -> dict:
    return {"edge_type": et, "row": r, "col": c, "state": s.value}


@mcp.tool
def load(grid_text: str) -> dict:
    """
    Parse a Slitherlink puzzle in textual format and return a state handle.
    See core/parser.py for the grid syntax. All edges start as 'unknown'.
    """
    state = load_from_text(grid_text)
    handle = uuid.uuid4().hex[:8]
    _states[handle] = state
    _snapshots[handle] = {}
    return {
        "handle": handle,
        "num_rows": state.num_rows,
        "num_cols": state.num_cols,
        "numbered_cells": [
            {"row": r, "col": c, "number": n}
            for (r, c), n in state.cells.items()
        ],
    }


@mcp.tool
def render(handle: str, show_blocked: bool = True) -> dict:
    """Return the current state as ASCII text."""
    return {"ascii": core_render(_get(handle), show_blocked=show_blocked)}


@mcp.tool
def dimensions(handle: str) -> dict:
    """Return the number of cell rows and columns."""
    s = _get(handle)
    return {"num_rows": s.num_rows, "num_cols": s.num_cols}


@mcp.tool
def get_cell_number(handle: str, row: int, col: int) -> dict:
    """
    Return the number constraint at a cell, or null if the cell is unconstrained.
    """
    s = _get(handle)
    return {"number": s.cells.get((row, col))}


@mcp.tool
def list_numbered_cells(handle: str) -> dict:
    """List every numbered cell with its required line count."""
    s = _get(handle)
    return {
        "cells": [
            {"row": r, "col": c, "number": n}
            for (r, c), n in s.cells.items()
        ]
    }


@mcp.tool
def get_edge(handle: str, edge_type: str, row: int, col: int) -> dict:
    """
    Return the state of a single edge. edge_type is 'H' or 'V'. State is
    'unknown', 'line', or 'blocked'.
    """
    s = _get(handle)
    return {"state": s.get_edge(edge_type, row, col).value}


@mcp.tool
def set_edge(handle: str, edge_type: str, row: int, col: int, value: str) -> dict:
    """
    Set a single edge to 'line' or 'blocked'. NO propagation, NO inference,
    NO consistency check beyond rejecting an overwrite of an existing
    different value (you must reset to 'unknown' first if you want to change
    your mind).

    Returns:
        previous: the prior state of the edge.
    """
    s = _get(handle)
    target = EdgeState(value)
    current = s.get_edge(edge_type, row, col)
    if current != EdgeState.UNKNOWN and current != target:
        raise ValueError(
            f"edge {edge_type}[{row}][{col}] is already {current.value}; "
            f"cannot overwrite with {target.value}"
        )
    s.set_edge(edge_type, row, col, target)
    return {"previous": current.value}


@mcp.tool
def reset_edge(handle: str, edge_type: str, row: int, col: int) -> dict:
    """Reset a single edge to 'unknown'. Useful after a mistaken set_edge."""
    s = _get(handle)
    previous = s.get_edge(edge_type, row, col)
    s.set_edge(edge_type, row, col, EdgeState.UNKNOWN)
    return {"previous": previous.value}


@mcp.tool
def count_edges_around_cell(handle: str, row: int, col: int) -> dict:
    """
    Count the line / blocked / unknown edges around a cell. Helpful for
    deciding whether the cell's constraint is satisfied / over-saturated.
    """
    s = _get(handle)
    counts = s.count_edges_around_cell(row, col)
    return {state.value: counts[state] for state in EdgeState}


@mcp.tool
def count_edges_at_dot(handle: str, dot_row: int, dot_col: int) -> dict:
    """
    Count the line / blocked / unknown edges incident to a dot. A solved
    puzzle has 0 or 2 line edges at every dot.
    """
    s = _get(handle)
    counts = s.count_edges_at_dot(dot_row, dot_col)
    return {state.value: counts[state] for state in EdgeState}


@mcp.tool
def list_edges_around_cell(handle: str, row: int, col: int) -> dict:
    """List the 4 edges around a cell with their current states."""
    s = _get(handle)
    return {
        "edges": [
            _edge_dict(et, r, c, s.get_edge(et, r, c))
            for (et, r, c) in s.edges_around_cell(row, col)
        ]
    }


@mcp.tool
def list_edges_at_dot(handle: str, dot_row: int, dot_col: int) -> dict:
    """List the (up to 4) edges incident to a dot with their current states."""
    s = _get(handle)
    return {
        "edges": [
            _edge_dict(et, r, c, s.get_edge(et, r, c))
            for (et, r, c) in s.edges_at_dot(dot_row, dot_col)
        ]
    }


@mcp.tool
def list_endpoints(handle: str) -> dict:
    """List dots that currently have exactly 1 line edge (open path endpoints)."""
    s = _get(handle)
    out = []
    for r in range(s.num_rows + 1):
        for c in range(s.num_cols + 1):
            if s.count_edges_at_dot(r, c)[EdgeState.LINE] == 1:
                out.append({"row": r, "col": c})
    return {"dots": out}


@mcp.tool
def list_full_dots(handle: str) -> dict:
    """List dots that have exactly 2 line edges (their other sides are forced blocked)."""
    s = _get(handle)
    out = []
    for r in range(s.num_rows + 1):
        for c in range(s.num_cols + 1):
            if s.count_edges_at_dot(r, c)[EdgeState.LINE] == 2:
                out.append({"row": r, "col": c})
    return {"dots": out}


@mcp.tool
def snapshot(handle: str, label: str | None = None) -> dict:
    """Save a copy of the current state under a snapshot id."""
    s = _get(handle)
    snap_id = uuid.uuid4().hex[:6]
    if label:
        snap_id = f"{label}-{snap_id}"
    _snapshots[handle][snap_id] = s.clone()
    return {"snap_id": snap_id, "snapshots": list(_snapshots[handle].keys())}


@mcp.tool
def restore(handle: str, snap_id: str) -> dict:
    """Restore the state from a previously saved snapshot."""
    snaps = _snapshots.get(handle, {})
    if snap_id not in snaps:
        raise ValueError(
            f"unknown snap_id {snap_id!r}; available: {list(snaps.keys())}"
        )
    _states[handle] = snaps[snap_id].clone()
    return {"ok": True}


@mcp.tool
def solved(handle: str) -> dict:
    """Check whether the puzzle is fully solved. Returns {solved, reason}."""
    ok, reason = core_is_solved(_get(handle))
    return {"solved": ok, "reason": reason}


if __name__ == "__main__":
    mcp.run()
