from core.state import EdgeState, SlitherlinkState


def render(state: SlitherlinkState, show_blocked: bool = True) -> str:
    """
    Render the state as ASCII text.

    Conventions:
      +   +   +    dots
      ---          horizontal LINE edge
       x           horizontal BLOCKED edge (only if show_blocked)
      |            vertical LINE edge
      x            vertical BLOCKED edge (in dot column, between '+' rows; show_blocked)
      digits 0-3   cell number
      .            unconstrained cell (no number)
    """
    lines: list[str] = []
    for dot_row in range(state.num_rows + 1):
        # Dot row
        parts = ["+"]
        for col in range(state.num_cols):
            edge = state.h_edges[(dot_row, col)]
            if edge == EdgeState.LINE:
                parts.append("---")
            elif edge == EdgeState.BLOCKED and show_blocked:
                parts.append(" x ")
            else:
                parts.append("   ")
            parts.append("+")
        lines.append("".join(parts))

        if dot_row == state.num_rows:
            break

        # Cell row
        parts = []
        for dot_col in range(state.num_cols + 1):
            edge = state.v_edges[(dot_row, dot_col)]
            if edge == EdgeState.LINE:
                parts.append("|")
            elif edge == EdgeState.BLOCKED and show_blocked:
                parts.append("x")
            else:
                parts.append(" ")
            if dot_col < state.num_cols:
                cell_value = state.cells.get((dot_row, dot_col))
                parts.append(f" {cell_value} " if cell_value is not None else " . ")
        lines.append("".join(parts))

    return "\n".join(lines)
