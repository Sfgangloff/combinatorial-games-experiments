"""
slitherlink-scratchpad MCP server.

Same local-deduction primitives as `slitherlink-medium` (load, render,
apply_edge, forced_moves, check_consistency, endpoints, solved), but the
snapshot/restore pair is replaced by a stack of named hypothesis frames.

Each `assume(rationale, edges)` clones the current top state, applies the
given edges with full local propagation, and pushes a new frame. Deduction
tools (apply_edge etc.) act on the top frame implicitly. `commit` collapses
the frame's deductions into the parent; `retract` discards them and offers
the negation of a single-edge assumption when the frame contradicted.

Hard cap of 5 nested frames. Designed to test whether engine-managed branch
state lets the model solve harder puzzles than `medium` at lower token cost.

Run as a stdio MCP server:
    python servers/slitherlink-scratchpad/server.py
"""
import uuid
from dataclasses import dataclass, field

from fastmcp import FastMCP

from core import (
    EdgeState,
    SlitherlinkState,
    apply_edge as core_apply_edge,
    check_consistency as core_check_consistency,
    endpoints as core_endpoints,
    forced_moves as core_forced_moves,
    is_solved as core_is_solved,
    load_from_text,
    render as core_render,
)

mcp = FastMCP("slitherlink-scratchpad")

MAX_FRAME_DEPTH = 5


@dataclass
class Frame:
    """One hypothesis frame on the stack."""
    frame_id: str
    parent_id: str | None
    rationale: str
    state: SlitherlinkState
    # Edges the model passed to assume(), with the propagation result for each.
    assumed_edges: list[dict] = field(default_factory=list)
    # 'open'  — propagation succeeded, frame is still active.
    # 'contradiction' — propagation hit a contradiction (frame still on stack).
    status: str = "open"
    # Set when status='contradiction', the (edge_type, row, col) that the model
    # asserted that ended up contradicting (the *first* one with a contradiction).
    contradicting_edge: dict | None = None


# Per-handle: the bottom of the stack is the root state (depth 0); frames
# pushed by `assume` sit above it. We always operate on stack[-1].state.
_states: dict[str, list[Frame]] = {}


def _stack(handle: str) -> list[Frame]:
    stk = _states.get(handle)
    if stk is None:
        raise ValueError(f"unknown handle: {handle!r}. Call load() first.")
    return stk


def _top(handle: str) -> SlitherlinkState:
    return _stack(handle)[-1].state


def _summary(state: SlitherlinkState) -> dict:
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


def _frame_dict(frame: Frame, depth: int) -> dict:
    return {
        "frame_id": frame.frame_id,
        "parent_id": frame.parent_id,
        "depth": depth,
        "rationale": frame.rationale,
        "status": frame.status,
        "assumed_edges": frame.assumed_edges,
        "contradicting_edge": frame.contradicting_edge,
    }


@mcp.tool
def load(grid_text: str) -> dict:
    """
    Parse a Slitherlink puzzle and return a state handle. The handle holds a
    frame stack whose bottom is the root state; assume() pushes new frames.

    Returns:
        handle: opaque string for this puzzle.
        summary: dimensions, cell-numbers grouped by value, edge counts, endpoints.
    """
    state = load_from_text(grid_text)
    handle = uuid.uuid4().hex[:8]
    root = Frame(
        frame_id="root",
        parent_id=None,
        rationale="root state (no hypothesis)",
        state=state,
        assumed_edges=[],
        status="open",
    )
    _states[handle] = [root]
    return {"handle": handle, "summary": _summary(state)}


@mcp.tool
def render(handle: str, show_blocked: bool = True) -> dict:
    """
    Return ASCII view of the current frame's state. 'x' marks blocked edges
    when show_blocked=True. Always reflects the *top* of the frame stack.
    """
    return {"ascii": core_render(_top(handle), show_blocked=show_blocked)}


@mcp.tool
def apply_edge(handle: str, edge_type: str, row: int, col: int, value: str) -> dict:
    """
    Set a single edge to LINE or BLOCKED in the current frame and propagate
    local rules to a fixed point. Same semantics as the medium toolset's
    apply_edge, but operates on whichever frame is on top.

    Args:
        edge_type: 'H' or 'V'.
        row, col: edge indexing (see core/state.py).
        value: 'line' or 'blocked'.

    Returns:
        changes: list of edge changes.
        contradiction: null on success, else a string. State is left as-is on
                       contradiction so it can be inspected before retract().
    """
    state = _top(handle)
    return core_apply_edge(state, edge_type, row, col, value).as_dict()


@mcp.tool
def forced_moves(handle: str) -> dict:
    """
    Preview edges that local rules currently force in the current frame,
    without mutating it.
    """
    return core_forced_moves(_top(handle)).as_dict()


@mcp.tool
def check_consistency(handle: str) -> dict:
    """
    Detect violations in the current frame: over-/under-satisfied cells, dots
    with too many line edges, multiple open path components, premature loop
    closure with unsatisfied cells. Empty list = no local-rule violations.
    """
    return {"issues": core_check_consistency(_top(handle))}


@mcp.tool
def endpoints(handle: str) -> dict:
    """
    Dots with exactly one line edge in the current frame. A solved puzzle has
    zero endpoints.
    """
    return {"dots": [[r, c] for (r, c) in core_endpoints(_top(handle))]}


@mcp.tool
def solved(handle: str) -> dict:
    """Whether the current frame is a complete, valid solution."""
    ok, reason = core_is_solved(_top(handle))
    return {"solved": ok, "reason": reason}


@mcp.tool
def assume(handle: str, rationale: str, edges: list[dict]) -> dict:
    """
    Open a new hypothesis frame. Clones the current top state, applies the
    given edges in order with full local propagation after each, then pushes
    the result onto the stack.

    Args:
        rationale: short, human-readable explanation of WHY you are testing
                   this hypothesis. Becomes part of the frame and shows up in
                   frames() / current_frame() so the engine can carry context
                   you would otherwise have to remember in tokens.
        edges: list of {edge_type: 'H'|'V', row: int, col: int, value: 'line'|'blocked'}.
               Each is applied with propagation; if any of them (or its
               propagated consequences) contradicts, the frame is left on the
               stack with status='contradiction' and contradicting_edge set
               to that edge. You can then retract() to pop, optionally taking
               the engine's offered negation as a free deduction at the
               parent level.

    Returns:
        frame_id, depth, summary (of the frame's state), assumed_edges (per-edge
        changes), contradiction (null if frame is open and consistent), and
        status ('open' | 'contradiction').

    Errors:
        - depth would exceed 5: caller must commit() or retract() first.
        - empty edges list: must commit to at least one edge.
    """
    stk = _stack(handle)
    if len(stk) >= MAX_FRAME_DEPTH + 1:  # +1 because root is depth 0
        return {
            "error": (
                f"frame stack already at max depth {MAX_FRAME_DEPTH}. "
                f"commit() or retract() before opening a new frame."
            ),
            "depth": len(stk) - 1,
        }
    if not edges:
        return {"error": "assume() requires at least one edge in `edges`."}

    parent = stk[-1]
    new_state = parent.state.clone()
    frame_id = uuid.uuid4().hex[:6]
    frame = Frame(
        frame_id=frame_id,
        parent_id=parent.frame_id,
        rationale=rationale,
        state=new_state,
        assumed_edges=[],
        status="open",
    )

    contradiction: str | None = None
    for spec in edges:
        try:
            edge_type = spec["edge_type"]
            row = int(spec["row"])
            col = int(spec["col"])
            value = spec["value"]
        except (KeyError, TypeError, ValueError) as e:
            return {
                "error": f"malformed edge spec {spec!r}: {e}",
                "applied_so_far": frame.assumed_edges,
            }
        result = core_apply_edge(new_state, edge_type, row, col, value)
        frame.assumed_edges.append({
            "edge_type": edge_type,
            "row": row,
            "col": col,
            "value": value,
            "changes": [c.as_dict() for c in result.changes],
            "contradiction": result.contradiction,
        })
        if result.contradiction is not None:
            contradiction = result.contradiction
            frame.status = "contradiction"
            frame.contradicting_edge = {
                "edge_type": edge_type, "row": row, "col": col, "value": value,
            }
            break

    stk.append(frame)
    depth = len(stk) - 1
    return {
        "frame_id": frame_id,
        "depth": depth,
        "status": frame.status,
        "summary": _summary(frame.state),
        "assumed_edges": frame.assumed_edges,
        "contradiction": contradiction,
    }


@mcp.tool
def commit(handle: str, frame_id: str) -> dict:
    """
    Collapse the top frame's deductions into its parent. Only valid when the
    frame is the top of the stack and has status='open' (no contradiction).
    The frame's state replaces the parent's state.

    Errors if frame_id is not the top, or the top frame has a contradiction
    (use retract instead).
    """
    stk = _stack(handle)
    if len(stk) <= 1:
        return {"error": "no frame to commit; only the root state is on the stack."}
    top = stk[-1]
    if top.frame_id != frame_id:
        return {
            "error": (
                f"frame_id {frame_id!r} is not the top frame "
                f"(top is {top.frame_id!r}). Operations only allowed on top."
            )
        }
    if top.status != "open":
        return {
            "error": (
                f"frame {frame_id!r} has status {top.status!r}; cannot commit. "
                f"Use retract instead."
            )
        }
    # Replace parent's state with the frame's state, drop the frame.
    parent = stk[-2]
    parent.state = top.state
    stk.pop()
    return {
        "ok": True,
        "depth": len(stk) - 1,
        "summary": _summary(parent.state),
    }


@mcp.tool
def retract(handle: str, frame_id: str, take_negation: bool = True) -> dict:
    """
    Pop the top frame, discarding its deductions. If the frame contradicted
    AND it had exactly one assumed edge, the engine offers the negation of
    that edge as a free deduction at the parent level: the assumption was
    false, so the opposite must hold. Pass take_negation=False to decline
    (e.g. you suspect the contradiction was spurious).

    Args:
        frame_id: must equal the top frame.
        take_negation: if True (default) and the frame contradicted with a
                       single assumed edge, apply the negated edge to the
                       parent state with full propagation.

    Returns:
        ok: True.
        depth: new stack depth.
        negation_applied: null, or {edge_type, row, col, value, changes,
                          contradiction} if a negation was applied to the
                          parent.
        summary: updated parent state summary.
    """
    stk = _stack(handle)
    if len(stk) <= 1:
        return {"error": "no frame to retract; only the root state is on the stack."}
    top = stk[-1]
    if top.frame_id != frame_id:
        return {
            "error": (
                f"frame_id {frame_id!r} is not the top frame "
                f"(top is {top.frame_id!r})."
            )
        }

    stk.pop()
    parent = stk[-1]
    negation_applied: dict | None = None

    eligible = (
        take_negation
        and top.status == "contradiction"
        and len(top.assumed_edges) == 1
        and top.contradicting_edge is not None
    )
    if eligible:
        ce = top.contradicting_edge
        opposite = "blocked" if ce["value"] == "line" else "line"
        result = core_apply_edge(parent.state, ce["edge_type"], ce["row"], ce["col"], opposite)
        negation_applied = {
            "edge_type": ce["edge_type"],
            "row": ce["row"],
            "col": ce["col"],
            "value": opposite,
            "changes": [c.as_dict() for c in result.changes],
            "contradiction": result.contradiction,
        }

    return {
        "ok": True,
        "depth": len(stk) - 1,
        "negation_applied": negation_applied,
        "summary": _summary(parent.state),
    }


@mcp.tool
def frames(handle: str) -> dict:
    """
    List all frames on the stack from root (depth 0) to top. Each entry shows
    frame_id, parent_id, depth, rationale, status, assumed_edges, and
    contradicting_edge. Use this to recover branch context without holding it
    in tokens.
    """
    stk = _stack(handle)
    return {
        "depth": len(stk) - 1,
        "max_depth": MAX_FRAME_DEPTH,
        "frames": [_frame_dict(f, i) for i, f in enumerate(stk)],
    }


@mcp.tool
def current_frame(handle: str) -> dict:
    """
    Return the top frame plus its full ancestry chain (root → … → top). Like
    frames() but emphasizes "where am I right now."
    """
    stk = _stack(handle)
    return {
        "depth": len(stk) - 1,
        "max_depth": MAX_FRAME_DEPTH,
        "ancestry": [_frame_dict(f, i) for i, f in enumerate(stk)],
    }


if __name__ == "__main__":
    mcp.run()
