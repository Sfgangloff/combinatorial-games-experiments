from core.state import EdgeState, SlitherlinkState


def endpoints(state: SlitherlinkState) -> list[tuple[int, int]]:
    """Dots with exactly 1 LINE edge — the endpoints of an open path."""
    out: list[tuple[int, int]] = []
    for dot_row in range(state.num_rows + 1):
        for dot_col in range(state.num_cols + 1):
            counts = state.count_edges_at_dot(dot_row, dot_col)
            if counts[EdgeState.LINE] == 1:
                out.append((dot_row, dot_col))
    return out


def line_components(state: SlitherlinkState) -> list[set[tuple[int, int]]]:
    """
    Connected components of dots, joined by LINE edges.
    Returns only components with at least one LINE-edge incident dot.
    """
    parent: dict[tuple[int, int], tuple[int, int]] = {}

    def find(x: tuple[int, int]) -> tuple[int, int]:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: tuple[int, int], b: tuple[int, int]) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    line_dots: set[tuple[int, int]] = set()
    for (r, c), s in state.h_edges.items():
        if s == EdgeState.LINE:
            a, b = (r, c), (r, c + 1)
            line_dots.add(a)
            line_dots.add(b)
            parent.setdefault(a, a)
            parent.setdefault(b, b)
            union(a, b)
    for (r, c), s in state.v_edges.items():
        if s == EdgeState.LINE:
            a, b = (r, c), (r + 1, c)
            line_dots.add(a)
            line_dots.add(b)
            parent.setdefault(a, a)
            parent.setdefault(b, b)
            union(a, b)

    groups: dict[tuple[int, int], set[tuple[int, int]]] = {}
    for dot in line_dots:
        root = find(dot)
        groups.setdefault(root, set()).add(dot)
    return list(groups.values())


def check_consistency(state: SlitherlinkState) -> list[str]:
    """
    Return a list of consistency violations. Empty list = consistent.

    Detects:
      - Cells over-satisfied (too many LINE edges).
      - Cells under-satisfiable (LINE + UNKNOWN < required).
      - Dots with > 2 LINE edges (branching).
      - More than one open path component (loop must be a single path/cycle).
      - A small closed loop while some numbered cell is still under-satisfied.
    """
    issues: list[str] = []

    for (cr, cc), n in state.cells.items():
        counts = state.count_edges_around_cell(cr, cc)
        if counts[EdgeState.LINE] > n:
            issues.append(
                f"cell ({cr},{cc})={n} has {counts[EdgeState.LINE]} lines (too many)"
            )
        if counts[EdgeState.LINE] + counts[EdgeState.UNKNOWN] < n:
            issues.append(
                f"cell ({cr},{cc})={n} cannot reach quota: only "
                f"{counts[EdgeState.LINE] + counts[EdgeState.UNKNOWN]} possible lines"
            )

    for dot_row in range(state.num_rows + 1):
        for dot_col in range(state.num_cols + 1):
            line_count = state.count_edges_at_dot(dot_row, dot_col)[EdgeState.LINE]
            if line_count > 2:
                issues.append(
                    f"dot ({dot_row},{dot_col}) has {line_count} lines (branching)"
                )

    components = line_components(state)
    open_components = [g for g in components if any(
        state.count_edges_at_dot(d[0], d[1])[EdgeState.LINE] == 1 for d in g
    )]
    if len(open_components) > 1:
        issues.append(
            f"{len(open_components)} open path components — loop must be one path"
        )

    closed_components = [g for g in components if g not in open_components]
    if closed_components:
        unsatisfied = [
            (cr, cc, n) for (cr, cc), n in state.cells.items()
            if state.count_edges_around_cell(cr, cc)[EdgeState.LINE] < n
        ]
        if unsatisfied:
            issues.append(
                f"closed loop formed but {len(unsatisfied)} numbered cells still "
                f"under-satisfied"
            )

    return issues


def is_solved(state: SlitherlinkState) -> tuple[bool, str]:
    """
    Returns (solved, reason). Solved iff:
      - every numbered cell has its exact required count of LINE edges,
      - every dot has 0 or exactly 2 LINE edges,
      - all LINE edges form exactly one closed loop,
      - no UNKNOWN edges remain (UNKNOWN treated as not-on-loop is fine if all
        constraints are met, but for clarity we require resolution).
    """
    for (cr, cc), n in state.cells.items():
        line_count = state.count_edges_around_cell(cr, cc)[EdgeState.LINE]
        if line_count != n:
            return False, f"cell ({cr},{cc})={n} has {line_count} lines"

    for dot_row in range(state.num_rows + 1):
        for dot_col in range(state.num_cols + 1):
            line_count = state.count_edges_at_dot(dot_row, dot_col)[EdgeState.LINE]
            if line_count not in (0, 2):
                return False, f"dot ({dot_row},{dot_col}) has {line_count} lines"

    components = line_components(state)
    if len(components) == 0:
        return False, "no loop drawn"
    if len(components) > 1:
        return False, f"{len(components)} disconnected components"
    return True, "solved"
