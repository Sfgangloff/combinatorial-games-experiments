from dataclasses import dataclass

from core.state import EdgeState, SlitherlinkState


@dataclass
class EdgeChange:
    edge_type: str          # "H" or "V"
    row: int
    col: int
    new_state: EdgeState
    reason: str             # short, human-readable rule explanation

    def as_dict(self) -> dict:
        return {
            "edge": f"{self.edge_type}[{self.row}][{self.col}]",
            "edge_type": self.edge_type,
            "row": self.row,
            "col": self.col,
            "new_state": self.new_state.value,
            "reason": self.reason,
        }


@dataclass
class PropagationResult:
    changes: list[EdgeChange]
    contradiction: str | None = None  # None if consistent

    def as_dict(self) -> dict:
        return {
            "changes": [c.as_dict() for c in self.changes],
            "contradiction": self.contradiction,
        }


def _set_with_check(
    state: SlitherlinkState,
    edge_type: str,
    row: int,
    col: int,
    target: EdgeState,
    reason: str,
    changes: list[EdgeChange],
) -> str | None:
    """Set an edge, returning a contradiction string if it conflicts."""
    current = state.get_edge(edge_type, row, col)
    if current == target:
        return None
    if current != EdgeState.UNKNOWN:
        return (
            f"Edge {edge_type}[{row}][{col}] is {current.value} but rule "
            f"forces {target.value} ({reason})"
        )
    state.set_edge(edge_type, row, col, target)
    changes.append(EdgeChange(edge_type, row, col, target, reason))
    return None


def _propagate_cell(
    state: SlitherlinkState,
    cell_row: int,
    cell_col: int,
    changes: list[EdgeChange],
) -> str | None:
    n = state.cells.get((cell_row, cell_col))
    if n is None:
        return None
    counts = state.count_edges_around_cell(cell_row, cell_col)
    line = counts[EdgeState.LINE]
    blocked = counts[EdgeState.BLOCKED]
    unknown = counts[EdgeState.UNKNOWN]

    if line > n:
        return f"Cell ({cell_row},{cell_col})={n} has {line} lines (too many)"
    if 4 - blocked < n:
        return f"Cell ({cell_row},{cell_col})={n} can fit at most {4 - blocked} lines"

    edges = state.edges_around_cell(cell_row, cell_col)

    if line == n and unknown > 0:
        for et, r, c in edges:
            if state.get_edge(et, r, c) == EdgeState.UNKNOWN:
                err = _set_with_check(
                    state, et, r, c, EdgeState.BLOCKED,
                    f"cell ({cell_row},{cell_col})={n} already satisfied",
                    changes,
                )
                if err:
                    return err
        return None

    if line + unknown == n and unknown > 0:
        for et, r, c in edges:
            if state.get_edge(et, r, c) == EdgeState.UNKNOWN:
                err = _set_with_check(
                    state, et, r, c, EdgeState.LINE,
                    f"cell ({cell_row},{cell_col})={n} needs all remaining edges",
                    changes,
                )
                if err:
                    return err
    return None


def _propagate_dot(
    state: SlitherlinkState,
    dot_row: int,
    dot_col: int,
    changes: list[EdgeChange],
) -> str | None:
    counts = state.count_edges_at_dot(dot_row, dot_col)
    line = counts[EdgeState.LINE]
    unknown = counts[EdgeState.UNKNOWN]

    if line > 2:
        return f"Dot ({dot_row},{dot_col}) has {line} lines (branching)"

    edges = state.edges_at_dot(dot_row, dot_col)

    if line == 2 and unknown > 0:
        for et, r, c in edges:
            if state.get_edge(et, r, c) == EdgeState.UNKNOWN:
                err = _set_with_check(
                    state, et, r, c, EdgeState.BLOCKED,
                    f"dot ({dot_row},{dot_col}) already has 2 lines",
                    changes,
                )
                if err:
                    return err
        return None

    if line == 1 and unknown == 1:
        for et, r, c in edges:
            if state.get_edge(et, r, c) == EdgeState.UNKNOWN:
                err = _set_with_check(
                    state, et, r, c, EdgeState.LINE,
                    f"dot ({dot_row},{dot_col}) has 1 line, needs continuation",
                    changes,
                )
                if err:
                    return err
        return None

    if line == 0 and unknown == 1:
        for et, r, c in edges:
            if state.get_edge(et, r, c) == EdgeState.UNKNOWN:
                err = _set_with_check(
                    state, et, r, c, EdgeState.BLOCKED,
                    f"dot ({dot_row},{dot_col}) cannot have a single edge",
                    changes,
                )
                if err:
                    return err
    return None


def propagate(state: SlitherlinkState) -> PropagationResult:
    """Iterate local rules to a fixed point. Mutates state."""
    changes: list[EdgeChange] = []
    while True:
        before = len(changes)
        for cell in list(state.cells.keys()):
            err = _propagate_cell(state, cell[0], cell[1], changes)
            if err:
                return PropagationResult(changes, err)
        for dot_row in range(state.num_rows + 1):
            for dot_col in range(state.num_cols + 1):
                err = _propagate_dot(state, dot_row, dot_col, changes)
                if err:
                    return PropagationResult(changes, err)
        if len(changes) == before:
            return PropagationResult(changes, None)


def apply_edge(
    state: SlitherlinkState,
    edge_type: str,
    row: int,
    col: int,
    value: str,
) -> PropagationResult:
    """
    Set a single edge (value: 'line' or 'blocked') and propagate local rules.
    Mutates state. If the edge or its consequences contradict prior state,
    returns a result with `contradiction` set; the state is left in the
    contradictory configuration so the caller can inspect it.
    """
    target = EdgeState(value)
    changes: list[EdgeChange] = []
    err = _set_with_check(state, edge_type, row, col, target, "user move", changes)
    if err:
        return PropagationResult(changes, err)
    result = propagate(state)
    return PropagationResult(changes + result.changes, result.contradiction)


def forced_moves(state: SlitherlinkState) -> PropagationResult:
    """
    Return the moves that local rules force right now, without mutating state.
    """
    clone = state.clone()
    return propagate(clone)
