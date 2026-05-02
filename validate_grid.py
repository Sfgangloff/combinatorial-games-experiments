#!/usr/bin/env python3
"""
Slitherlink grid validator.
Checks that a partially filled grid does not violate the rules:
1. No dot has more than 2 edges (no branchings)
2. No cell has more edges than its number constraint
"""

def parse_grid(grid_text):
    """
    Parse the grid text format into edges and cell values.

    Grid format (NxM example):
    +   +---+   +   +      <- dot row 0
      .   3   .   2        <- cell row 0
    +   +   +   +   +      <- dot row 1
      .   .   3   .        <- cell row 1
    ...

    Each dot row has (num_cols + 1) '+' symbols.
    Horizontal edges are '---' between consecutive '+'.
    Vertical edges are '|' in cell rows at dot column positions.

    Returns:
        h_edges: set of (dot_row, col) for horizontal edges
        v_edges: set of (cell_row, col) for vertical edges
        cells: dict of (cell_row, col) -> int for numbered cells
        num_dot_rows: number of dot rows (num_cell_rows + 1)
        num_cols: number of columns
    """
    lines = grid_text.strip().split('\n')

    h_edges = set()  # horizontal edges: (dot_row, col) means edge from dot (dot_row, col) to (dot_row, col+1)
    v_edges = set()  # vertical edges: (cell_row, col) means edge from dot (cell_row, col) to (cell_row+1, col)
    cells = {}       # cell values: (cell_row, col) -> number

    dot_row = 0
    cell_row = 0
    num_cols = 0  # will be detected from first line

    for line_idx, line in enumerate(lines):
        if line_idx % 2 == 0:
            # Dot row - parse horizontal edges
            # Find all '+' positions first
            plus_positions = [i for i, c in enumerate(line) if c == '+']
            num_cols = len(plus_positions) - 1

            # Check for edges between consecutive '+' symbols
            for col in range(len(plus_positions) - 1):
                start = plus_positions[col]
                end = plus_positions[col + 1]
                segment = line[start:end+1]
                if '---' in segment:
                    h_edges.add((dot_row, col))

            dot_row += 1
        else:
            # Cell row - parse vertical edges and cell values
            # The format uses fixed-width columns (4 chars per cell typically)
            # Look for '|' characters and digit characters

            col = 0
            i = 0
            while i < len(line):
                char = line[i]
                if char == '|':
                    v_edges.add((cell_row, col))
                    i += 1
                elif char in '0123':
                    # This number belongs to cell at (cell_row, col-1) or current position
                    # Need to figure out which column this is in
                    # Count how many '|' or spaces we've passed
                    cells[(cell_row, col)] = int(char)
                    i += 1
                elif char == '.':
                    # Empty cell marker - advance to next cell
                    col += 1
                    i += 1
                elif char == ' ':
                    i += 1
                else:
                    i += 1

            # Check if line ends with '|' for right boundary
            stripped = line.rstrip()
            if stripped and stripped[-1] == '|':
                # Count columns to determine position
                pipe_count = stripped.count('|')
                # The last '|' is at column = num_cols
                v_edges.add((cell_row, num_cols))

            cell_row += 1

    return h_edges, v_edges, cells, dot_row, num_cols


def parse_grid_v2(grid_text):
    """
    Simpler parser using fixed column positions.

    Grid size is auto-detected from the first line.
    - Dot columns are at '+' positions (typically every 4 chars)
    - Cell values are between dots
    """
    lines = grid_text.strip().split('\n')

    h_edges = set()
    v_edges = set()
    cells = {}

    # Detect grid size from first line
    first_line = lines[0]
    plus_positions = [i for i, c in enumerate(first_line) if c == '+']
    num_cols = len(plus_positions) - 1

    dot_row = 0
    cell_row = 0

    for line_idx, line in enumerate(lines):
        # Pad line to ensure we can index safely
        line = line.ljust(80)

        if line_idx % 2 == 0:
            # Dot row
            for col in range(num_cols):
                # Check between dot positions for '---'
                if col < len(plus_positions) - 1:
                    start = plus_positions[col]
                    end = plus_positions[col + 1] if col + 1 < len(plus_positions) else start + 4
                    segment = line[start:end]
                    if '---' in segment:
                        h_edges.add((dot_row, col))
            dot_row += 1
        else:
            # Cell row
            for col in range(num_cols + 1):
                # Check for vertical edge at this column position
                if col < len(plus_positions):
                    pos = plus_positions[col]
                    if pos < len(line) and line[pos] == '|':
                        v_edges.add((cell_row, col))

            # Parse cell values
            for col in range(num_cols):
                if col < len(plus_positions) - 1:
                    start = plus_positions[col] + 1
                    end = plus_positions[col + 1]
                    segment = line[start:end]
                    for c in segment:
                        if c in '0123':
                            cells[(cell_row, col)] = int(c)
                            break

            cell_row += 1

    num_dot_rows = dot_row
    return h_edges, v_edges, cells, num_dot_rows, num_cols


def count_edges_at_dot(h_edges, v_edges, dot_row, dot_col, num_dot_rows, num_cols):
    """
    Count edges touching dot at (dot_row, dot_col).

    Edges touching this dot:
    - H edge to left: (dot_row, dot_col-1)
    - H edge to right: (dot_row, dot_col)
    - V edge above: (dot_row-1, dot_col)  [cell_row = dot_row-1]
    - V edge below: (dot_row, dot_col)    [cell_row = dot_row]
    """
    count = 0

    # Horizontal edge to the left
    if dot_col > 0 and (dot_row, dot_col - 1) in h_edges:
        count += 1

    # Horizontal edge to the right
    if dot_col < num_cols and (dot_row, dot_col) in h_edges:
        count += 1

    # Vertical edge above (from previous cell row)
    if dot_row > 0 and (dot_row - 1, dot_col) in v_edges:
        count += 1

    # Vertical edge below (from current cell row)
    if dot_row < num_dot_rows - 1 and (dot_row, dot_col) in v_edges:
        count += 1

    return count


def count_edges_for_cell(h_edges, v_edges, cell_row, cell_col):
    """
    Count edges around cell at (cell_row, cell_col).

    Edges around this cell:
    - Top: H edge (cell_row, cell_col)       [dot_row = cell_row]
    - Bottom: H edge (cell_row+1, cell_col)  [dot_row = cell_row+1]
    - Left: V edge (cell_row, cell_col)
    - Right: V edge (cell_row, cell_col+1)
    """
    count = 0

    # Top edge
    if (cell_row, cell_col) in h_edges:
        count += 1

    # Bottom edge
    if (cell_row + 1, cell_col) in h_edges:
        count += 1

    # Left edge
    if (cell_row, cell_col) in v_edges:
        count += 1

    # Right edge
    if (cell_row, cell_col + 1) in v_edges:
        count += 1

    return count


def validate_format(grid_text):
    """
    Validate the grid format itself.

    Checks:
    1. In dot rows: only '+', '-', and spaces allowed
    2. In cell rows: '|' only at dot column positions, not in cell content areas

    Returns:
        list of format error messages
    """
    lines = grid_text.strip().split('\n')
    errors = []

    if not lines:
        return ["Empty grid"]

    # Get dot positions from first line
    first_line = lines[0]
    plus_positions = [i for i, c in enumerate(first_line) if c == '+']

    if len(plus_positions) < 2:
        return ["Invalid grid: need at least 2 '+' symbols in first row"]

    for line_idx, line in enumerate(lines):
        if line_idx % 2 == 0:
            # Dot row - should only have '+', '-', and spaces
            for i, c in enumerate(line):
                if c not in '+- ':
                    errors.append(f"FORMAT ERROR line {line_idx+1} pos {i}: unexpected '{c}' in dot row (only '+', '-', space allowed)")
        else:
            # Cell row - '|' should only appear at dot column positions
            for i, c in enumerate(line):
                if c == '|':
                    # Check if this position is a valid dot column
                    if i not in plus_positions:
                        errors.append(f"FORMAT ERROR line {line_idx+1} pos {i}: '|' at invalid position (should be at dot columns: {plus_positions})")

    return errors


def is_edge_available(h_edges, v_edges, edge_type, edge_pos, num_dot_rows, num_cols):
    """
    Check if an edge can still be added (both endpoint dots have < 2 edges).

    Args:
        edge_type: 'h' for horizontal, 'v' for vertical
        edge_pos: (row, col) tuple for the edge

    Returns:
        True if the edge can be added, False otherwise
    """
    row, col = edge_pos

    if edge_type == 'h':
        # Horizontal edge from dot (row, col) to (row, col+1)
        # Check if edge already exists
        if edge_pos in h_edges:
            return False
        # Check both endpoint dots
        dot1_count = count_edges_at_dot(h_edges, v_edges, row, col, num_dot_rows, num_cols)
        dot2_count = count_edges_at_dot(h_edges, v_edges, row, col + 1, num_dot_rows, num_cols)
        return dot1_count < 2 and dot2_count < 2
    else:  # vertical
        # Vertical edge from dot (row, col) to (row+1, col)
        # Check if edge already exists
        if edge_pos in v_edges:
            return False
        # Check both endpoint dots
        dot1_count = count_edges_at_dot(h_edges, v_edges, row, col, num_dot_rows, num_cols)
        dot2_count = count_edges_at_dot(h_edges, v_edges, row + 1, col, num_dot_rows, num_cols)
        return dot1_count < 2 and dot2_count < 2


def get_cell_edges(cell_row, cell_col):
    """
    Get all 4 edges for a cell as (type, position) tuples.

    Returns list of ('h'|'v', (row, col)) for each edge:
    - Top: H edge at (cell_row, cell_col)
    - Bottom: H edge at (cell_row+1, cell_col)
    - Left: V edge at (cell_row, cell_col)
    - Right: V edge at (cell_row, cell_col+1)
    """
    return [
        ('h', (cell_row, cell_col)),        # Top
        ('h', (cell_row + 1, cell_col)),    # Bottom
        ('v', (cell_row, cell_col)),        # Left
        ('v', (cell_row, cell_col + 1)),    # Right
    ]


def get_available_edges_for_cell(h_edges, v_edges, cell_row, cell_col, num_dot_rows, num_cols):
    """
    Get list of edges that can still be added to a cell.

    Returns list of (edge_type, edge_pos, edge_name) tuples for available edges.
    """
    available = []
    edges = get_cell_edges(cell_row, cell_col)
    edge_names = ['top H', 'bottom H', 'left V', 'right V']

    for (edge_type, edge_pos), name in zip(edges, edge_names):
        if is_edge_available(h_edges, v_edges, edge_type, edge_pos, num_dot_rows, num_cols):
            available.append((edge_type, edge_pos, name))

    return available


def get_current_edges_for_cell(h_edges, v_edges, cell_row, cell_col):
    """
    Get list of edges currently present for a cell.
    """
    current = []
    edges = get_cell_edges(cell_row, cell_col)
    edge_names = ['top H', 'bottom H', 'left V', 'right V']

    for (edge_type, edge_pos), name in zip(edges, edge_names):
        edge_set = h_edges if edge_type == 'h' else v_edges
        if edge_pos in edge_set:
            current.append((edge_type, edge_pos, name))

    return current


def check_cell_satisfiability_with_propagation(h_edges, v_edges, cells, num_dot_rows, num_cols):
    """
    Check if all cells can be satisfied simultaneously by propagating forced edges.

    This is more thorough than simple satisfiability - it simulates adding forced edges
    and checks if that creates new unsatisfiable cells.

    Returns:
        list of error messages for unsatisfiable cells
    """
    # Work with copies so we can simulate adding edges
    h_edges_sim = set(h_edges)
    v_edges_sim = set(v_edges)
    errors = []

    # Iteratively find and add forced edges until no more changes
    max_iterations = 20  # Prevent infinite loops
    for iteration in range(max_iterations):
        changed = False

        for (cell_row, cell_col), constraint in cells.items():
            current_edges = get_current_edges_for_cell(h_edges_sim, v_edges_sim, cell_row, cell_col)
            current_count = len(current_edges)

            if current_count >= constraint:
                continue  # Cell already satisfied

            available_edges = get_available_edges_for_cell(h_edges_sim, v_edges_sim, cell_row, cell_col, num_dot_rows, num_cols)
            available_count = len(available_edges)
            needed = constraint - current_count

            if current_count + available_count < constraint:
                error_msg = (
                    f"UNSATISFIABLE cell ({cell_row},{cell_col})={constraint}: "
                    f"has {current_count} edges, can add {available_count} more, needs {constraint} total"
                )
                if error_msg not in errors:
                    errors.append(error_msg)
            elif available_count == needed:
                # These edges are forced - simulate adding them
                for edge_type, edge_pos, _ in available_edges:
                    if edge_type == 'h':
                        if edge_pos not in h_edges_sim:
                            h_edges_sim.add(edge_pos)
                            changed = True
                    else:
                        if edge_pos not in v_edges_sim:
                            v_edges_sim.add(edge_pos)
                            changed = True

        if not changed:
            break

    return errors


def check_cell_satisfiability(h_edges, v_edges, cells, num_dot_rows, num_cols):
    """
    Check if each numbered cell can still reach its target.

    For each cell with constraint N:
    1. Count current edges (C)
    2. Count available edges (A) - edges where BOTH endpoint dots have < 2 edges
    3. If C + A < N → UNSATISFIABLE

    Returns:
        list of error messages for unsatisfiable cells
    """
    errors = []

    for (cell_row, cell_col), constraint in cells.items():
        current_edges = get_current_edges_for_cell(h_edges, v_edges, cell_row, cell_col)
        current_count = len(current_edges)

        available_edges = get_available_edges_for_cell(h_edges, v_edges, cell_row, cell_col, num_dot_rows, num_cols)
        available_count = len(available_edges)

        if current_count + available_count < constraint:
            current_names = [e[2] for e in current_edges]
            available_names = [e[2] for e in available_edges]
            errors.append(
                f"UNSATISFIABLE cell ({cell_row},{cell_col})={constraint}: "
                f"has {current_count} edges {current_names}, "
                f"can add {available_count} more {available_names}, "
                f"needs {constraint} total"
            )

    return errors


def detect_forced_edges(h_edges, v_edges, cells, num_dot_rows, num_cols):
    """
    Detect edges that MUST be added to satisfy cell constraints.

    If a cell needs N more edges and has exactly N available edges,
    all those edges are forced.

    Returns:
        list of (cell_pos, constraint, forced_edges) tuples
    """
    forced = []

    for (cell_row, cell_col), constraint in cells.items():
        current_edges = get_current_edges_for_cell(h_edges, v_edges, cell_row, cell_col)
        current_count = len(current_edges)
        needed = constraint - current_count

        if needed <= 0:
            continue  # Cell already satisfied or over-satisfied

        available_edges = get_available_edges_for_cell(h_edges, v_edges, cell_row, cell_col, num_dot_rows, num_cols)
        available_count = len(available_edges)

        if available_count == needed:
            edge_names = [e[2] for e in available_edges]
            forced.append((
                (cell_row, cell_col),
                constraint,
                edge_names
            ))

    return forced


def validate_grid(grid_text, check_satisfiability=False):
    """
    Validate a Slitherlink grid.

    Returns:
        (is_valid, errors, warnings) where:
        - is_valid: True if no rule violations
        - errors: list of error messages
        - warnings: list of warning messages (forced edges, etc.)
    """
    # First check format
    format_errors = validate_format(grid_text)
    if format_errors:
        return False, format_errors, []

    h_edges, v_edges, cells, num_dot_rows, num_cols = parse_grid_v2(grid_text)
    errors = []
    warnings = []

    num_cell_rows = num_dot_rows - 1

    # Check all dots for branchings (more than 2 edges)
    for dot_row in range(num_dot_rows):
        for dot_col in range(num_cols + 1):
            edge_count = count_edges_at_dot(h_edges, v_edges, dot_row, dot_col, num_dot_rows, num_cols)
            if edge_count > 2:
                errors.append(f"BRANCHING at dot ({dot_row},{dot_col}): {edge_count} edges (max 2 allowed)")

    # Check all numbered cells don't exceed their constraint
    for (cell_row, cell_col), value in cells.items():
        edge_count = count_edges_for_cell(h_edges, v_edges, cell_row, cell_col)
        if edge_count > value:
            errors.append(f"CELL OVERFLOW at cell ({cell_row},{cell_col})={value}: has {edge_count} edges")

    # Check satisfiability if requested
    if check_satisfiability:
        # Use propagation-based check that simulates adding forced edges
        satisfiability_errors = check_cell_satisfiability_with_propagation(h_edges, v_edges, cells, num_dot_rows, num_cols)
        errors.extend(satisfiability_errors)

        # Detect forced edges (as warnings/hints) - only if no errors
        if not satisfiability_errors:
            forced = detect_forced_edges(h_edges, v_edges, cells, num_dot_rows, num_cols)
            for cell_pos, constraint, edge_names in forced:
                warnings.append(f"FORCED edges for cell {cell_pos}={constraint}: {edge_names}")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def validate_grid_file(filepath, check_satisfiability=False):
    """Validate a grid from a file."""
    with open(filepath, 'r') as f:
        grid_text = f.read()
    return validate_grid(grid_text, check_satisfiability=check_satisfiability)


# For debugging
def debug_parse(grid_text):
    """Print parsed edges for debugging."""
    h_edges, v_edges, cells, num_dot_rows, num_cols = parse_grid_v2(grid_text)
    print(f"Grid: {num_cols} cols, {num_dot_rows} dot rows ({num_dot_rows-1} cell rows)")
    print(f"H edges: {sorted(h_edges)}")
    print(f"V edges: {sorted(v_edges)}")
    print(f"Cells: {cells}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        check_sat = "--check-satisfiability" in sys.argv or "-s" in sys.argv

        if "--debug" in sys.argv:
            with open(filepath, 'r') as f:
                debug_parse(f.read())

        is_valid, errors, warnings = validate_grid_file(filepath, check_satisfiability=check_sat)

        if is_valid:
            print(f"✓ Grid is valid (no rule violations)")
            if check_sat:
                print(f"✓ All cells remain satisfiable")
        else:
            print(f"✗ Grid has {len(errors)} violation(s):")
            for error in errors:
                print(f"  - {error}")

        # Show warnings (forced edges) if any
        if warnings:
            print(f"\n⚠ Hints ({len(warnings)} forced edge(s) detected):")
            for warning in warnings:
                print(f"  - {warning}")

        sys.exit(0 if is_valid else 1)
    else:
        print("Usage: python validate_grid.py <grid_file> [OPTIONS]")
        print("")
        print("Options:")
        print("  --check-satisfiability, -s  Check if all cells can still be satisfied")
        print("  --debug                     Print parsed edges for debugging")
        print("")
        print("Example: python validate_grid.py grid_step_1.txt")
        print("Example: python validate_grid.py grid_step_1.txt --check-satisfiability")
