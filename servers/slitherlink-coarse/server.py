"""
slitherlink-coarse MCP server.

Minimal high-level tools as a control condition. The flagship tool is
`suggest_next_move`, which (a) checks for moves forced by local rules and
returns one with a reason, or (b) does 1-ply lookahead: tries each unknown
edge in turn — if assuming 'line' propagates to a contradiction, the edge
must be 'blocked', and vice versa.

That's *not* SAT solving — it's the basic "try and see" technique a human
would use, depth 1 only. It still leaves room for the model to fail when
the puzzle requires deeper reasoning.

Run as a stdio MCP server:
    python servers/slitherlink-coarse/server.py
"""
from __future__ import annotations

import uuid

from fastmcp import FastMCP

from core import (
    EdgeState,
    SlitherlinkState,
    apply_edge as core_apply_edge,
    check_consistency as core_check_consistency,
    forced_moves as core_forced_moves,
    is_solved as core_is_solved,
    load_from_text,
    propagate,
    render as core_render,
)

mcp = FastMCP("slitherlink-coarse")

_states: dict[str, SlitherlinkState] = {}


def _get(handle: str) -> SlitherlinkState:
    state = _states.get(handle)
    if state is None:
        raise ValueError(f"unknown handle: {handle!r}. Call load() first.")
    return state


def _summary(state: SlitherlinkState) -> dict:
    line_h = sum(1 for s in state.h_edges.values() if s == EdgeState.LINE)
    line_v = sum(1 for s in state.v_edges.values() if s == EdgeState.LINE)
    blocked_h = sum(1 for s in state.h_edges.values() if s == EdgeState.BLOCKED)
    blocked_v = sum(1 for s in state.v_edges.values() if s == EdgeState.BLOCKED)
    unknown_h = sum(1 for s in state.h_edges.values() if s == EdgeState.UNKNOWN)
    unknown_v = sum(1 for s in state.v_edges.values() if s == EdgeState.UNKNOWN)
    return {
        "num_rows": state.num_rows,
        "num_cols": state.num_cols,
        "line_edges": line_h + line_v,
        "blocked_edges": blocked_h + blocked_v,
        "unknown_edges": unknown_h + unknown_v,
    }


def _lookahead_move(state: SlitherlinkState) -> dict | None:
    """
    1-ply lookahead. Returns a forced move {edge_type, row, col, value, reason}
    proven by contradiction, or None if no such move exists.
    """
    for (et, r, c) in state.all_edges():
        if state.get_edge(et, r, c) != EdgeState.UNKNOWN:
            continue
        # Try LINE.
        clone = state.clone()
        clone.set_edge(et, r, c, EdgeState.LINE)
        if propagate(clone).contradiction is not None:
            return {
                "edge_type": et,
                "row": r,
                "col": c,
                "value": "blocked",
                "reason": (
                    f"setting {et}[{r}][{c}]=line leads to contradiction "
                    f"after propagation, so it must be blocked"
                ),
            }
        # Try BLOCKED.
        clone = state.clone()
        clone.set_edge(et, r, c, EdgeState.BLOCKED)
        if propagate(clone).contradiction is not None:
            return {
                "edge_type": et,
                "row": r,
                "col": c,
                "value": "line",
                "reason": (
                    f"setting {et}[{r}][{c}]=blocked leads to contradiction "
                    f"after propagation, so it must be line"
                ),
            }
    return None


@mcp.tool
def load(grid_text: str) -> dict:
    """Parse a Slitherlink puzzle and return a state handle."""
    state = load_from_text(grid_text)
    handle = uuid.uuid4().hex[:8]
    _states[handle] = state
    return {"handle": handle, "summary": _summary(state)}


@mcp.tool
def state(handle: str) -> dict:
    """Return ASCII rendering and a numeric summary."""
    s = _get(handle)
    return {"ascii": core_render(s), "summary": _summary(s)}


@mcp.tool
def suggest_next_move(handle: str) -> dict:
    """
    Return one move that is provably correct given the current state, with a
    reason. The tool will:

      1. Look for moves forced by local rules (cell saturation, dot 0-or-2,
         single-line continuation). If any, return the first.
      2. Otherwise do 1-ply lookahead: try each unknown edge as line and as
         blocked; if one of those leads to a contradiction after propagating
         all local rules, the opposite is forced.
      3. If neither finds anything, return {move: null} — the puzzle requires
         deeper reasoning the tool won't attempt.

    Returns:
        move: {edge_type, row, col, value, reason} or null.
        method: 'forced' | 'lookahead' | 'stuck'.
    """
    s = _get(handle)
    forced = core_forced_moves(s)
    if forced.contradiction:
        return {"move": None, "method": "contradiction", "detail": forced.contradiction}
    if forced.changes:
        ch = forced.changes[0]
        return {
            "move": {
                "edge_type": ch.edge_type,
                "row": ch.row,
                "col": ch.col,
                "value": ch.new_state.value,
                "reason": ch.reason,
            },
            "method": "forced",
        }
    move = _lookahead_move(s)
    if move is not None:
        return {"move": move, "method": "lookahead"}
    return {"move": None, "method": "stuck"}


@mcp.tool
def apply_move(handle: str, edge_type: str, row: int, col: int, value: str) -> dict:
    """
    Set an edge to 'line' or 'blocked' and propagate local rules.
    Same semantics as medium's apply_edge.
    """
    s = _get(handle)
    return core_apply_edge(s, edge_type, row, col, value).as_dict()


@mcp.tool
def check_consistency(handle: str) -> dict:
    """List consistency violations (empty if none)."""
    return {"issues": core_check_consistency(_get(handle))}


@mcp.tool
def solved(handle: str) -> dict:
    """Return {solved, reason}."""
    ok, reason = core_is_solved(_get(handle))
    return {"solved": ok, "reason": reason}


if __name__ == "__main__":
    mcp.run()
