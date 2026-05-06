from core.state import SlitherlinkState


def load_from_text(grid_text: str) -> SlitherlinkState:
    """
    Parse a Slitherlink grid in the textual format used in this project:

        +   +   +   +   +   +
          3   .   .   2   .
        +   +   +   +   +   +
          .   2   1   3   3
        ...

    Dots are '+'. Numbers (0-3) and '.' (no constraint) appear in cell rows.
    Existing edges may be drawn with '---' (horizontal) and '|' (vertical),
    but new puzzles typically have no edges yet.

    Returns a SlitherlinkState with edges set to UNKNOWN unless drawn.
    """
    from core.state import EdgeState

    lines = [line for line in grid_text.split("\n") if line.strip() != ""]
    if not lines:
        raise ValueError("Empty grid text")

    plus_positions = [i for i, c in enumerate(lines[0]) if c == "+"]
    if len(plus_positions) < 2:
        raise ValueError("Invalid grid: first row must contain at least 2 '+' symbols")

    num_cols = len(plus_positions) - 1
    num_rows = (len(lines) - 1) // 2

    state = SlitherlinkState.empty(num_rows, num_cols)

    for line_idx, line in enumerate(lines):
        line = line.ljust(plus_positions[-1] + 2)
        if line_idx % 2 == 0:
            dot_row = line_idx // 2
            for col in range(num_cols):
                start = plus_positions[col]
                end = plus_positions[col + 1]
                segment = line[start:end + 1]
                if "---" in segment:
                    state.h_edges[(dot_row, col)] = EdgeState.LINE
        else:
            cell_row = line_idx // 2
            for dot_col, pos in enumerate(plus_positions):
                if pos < len(line) and line[pos] == "|":
                    state.v_edges[(cell_row, dot_col)] = EdgeState.LINE
            for col in range(num_cols):
                start = plus_positions[col] + 1
                end = plus_positions[col + 1]
                segment = line[start:end]
                for ch in segment:
                    if ch in "0123":
                        state.cells[(cell_row, col)] = int(ch)
                        break

    return state
