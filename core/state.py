from dataclasses import dataclass, field
from enum import Enum


class EdgeState(str, Enum):
    UNKNOWN = "unknown"
    LINE = "line"
    BLOCKED = "blocked"


@dataclass
class SlitherlinkState:
    """
    Slitherlink puzzle state.

    Coordinate system (1-indexed in source, 0-indexed here):
    - Cells: (cell_row, cell_col), 0 <= cell_row < num_rows, 0 <= cell_col < num_cols.
    - Dots: (dot_row, dot_col), 0 <= dot_row <= num_rows, 0 <= dot_col <= num_cols.
    - Horizontal edges H[dot_row][col]: top of cell (dot_row, col) / bottom of cell (dot_row-1, col).
      Indexed by (dot_row, col), 0 <= dot_row <= num_rows, 0 <= col < num_cols.
    - Vertical edges V[cell_row][dot_col]: right of cell (cell_row, dot_col-1) / left of (cell_row, dot_col).
      Indexed by (cell_row, dot_col), 0 <= cell_row < num_rows, 0 <= dot_col <= num_cols.
    """

    num_rows: int
    num_cols: int
    cells: dict[tuple[int, int], int] = field(default_factory=dict)
    h_edges: dict[tuple[int, int], EdgeState] = field(default_factory=dict)
    v_edges: dict[tuple[int, int], EdgeState] = field(default_factory=dict)

    @classmethod
    def empty(
        cls,
        num_rows: int,
        num_cols: int,
        cells: dict[tuple[int, int], int] | None = None,
    ) -> "SlitherlinkState":
        cells = dict(cells or {})
        h_edges = {
            (r, c): EdgeState.UNKNOWN
            for r in range(num_rows + 1)
            for c in range(num_cols)
        }
        v_edges = {
            (r, c): EdgeState.UNKNOWN
            for r in range(num_rows)
            for c in range(num_cols + 1)
        }
        return cls(num_rows, num_cols, cells, h_edges, v_edges)

    def clone(self) -> "SlitherlinkState":
        return SlitherlinkState(
            num_rows=self.num_rows,
            num_cols=self.num_cols,
            cells=dict(self.cells),
            h_edges=dict(self.h_edges),
            v_edges=dict(self.v_edges),
        )

    def edges_around_cell(
        self, cell_row: int, cell_col: int
    ) -> list[tuple[str, int, int]]:
        """Return the 4 edges around a cell as (type, row, col) tuples."""
        return [
            ("H", cell_row, cell_col),       # top
            ("H", cell_row + 1, cell_col),   # bottom
            ("V", cell_row, cell_col),       # left
            ("V", cell_row, cell_col + 1),   # right
        ]

    def edges_at_dot(self, dot_row: int, dot_col: int) -> list[tuple[str, int, int]]:
        """Return the (up to 4) edges incident to a dot."""
        out = []
        if dot_col > 0:
            out.append(("H", dot_row, dot_col - 1))   # left
        if dot_col < self.num_cols:
            out.append(("H", dot_row, dot_col))       # right
        if dot_row > 0:
            out.append(("V", dot_row - 1, dot_col))   # up
        if dot_row < self.num_rows:
            out.append(("V", dot_row, dot_col))       # down
        return out

    def get_edge(self, edge_type: str, row: int, col: int) -> EdgeState:
        if edge_type == "H":
            return self.h_edges[(row, col)]
        if edge_type == "V":
            return self.v_edges[(row, col)]
        raise ValueError(f"Unknown edge type: {edge_type!r}")

    def set_edge(self, edge_type: str, row: int, col: int, state: EdgeState) -> None:
        if edge_type == "H":
            self.h_edges[(row, col)] = state
        elif edge_type == "V":
            self.v_edges[(row, col)] = state
        else:
            raise ValueError(f"Unknown edge type: {edge_type!r}")

    def count_edges_around_cell(
        self, cell_row: int, cell_col: int
    ) -> dict[EdgeState, int]:
        counts = {EdgeState.UNKNOWN: 0, EdgeState.LINE: 0, EdgeState.BLOCKED: 0}
        for et, r, c in self.edges_around_cell(cell_row, cell_col):
            counts[self.get_edge(et, r, c)] += 1
        return counts

    def count_edges_at_dot(self, dot_row: int, dot_col: int) -> dict[EdgeState, int]:
        counts = {EdgeState.UNKNOWN: 0, EdgeState.LINE: 0, EdgeState.BLOCKED: 0}
        for et, r, c in self.edges_at_dot(dot_row, dot_col):
            counts[self.get_edge(et, r, c)] += 1
        return counts

    def all_edges(self) -> list[tuple[str, int, int]]:
        out: list[tuple[str, int, int]] = []
        for (r, c) in self.h_edges:
            out.append(("H", r, c))
        for (r, c) in self.v_edges:
            out.append(("V", r, c))
        return out
