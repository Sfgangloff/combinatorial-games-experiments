#!/usr/bin/env python3
"""
Batch Verifier for Slitherlink Solving

Verifies that a batch follows all MUST rules from CLAUDE.md:
1. File created: reasoning_step_N.txt
2. Exactly 5 steps (unless BACKTRACK)
3. Each step contains a full grid
4. Each grid differs from previous by exactly ONE edge change
5. Validator output section is present
6. Single path component (0 or 2 endpoints)
7. Validator passes on final grid

Usage: python3 verify_batch.py <batch_number>
"""

import sys
import os
import subprocess
import tempfile

def read_file(path):
    """Read file contents or return None if not exists."""
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return f.read()

def extract_grids_from_reasoning(content):
    """Extract all grids from reasoning file."""
    grids = []
    lines = content.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('Grid after step'):
            # Collect grid lines (start with + or contain . or numbers)
            grid_lines = []
            i += 1
            while i < len(lines):
                l = lines[i]
                # Grid lines start with + or have grid content
                if l.startswith('+') or (len(l) > 0 and (l[0] in ' |X' or l.strip().startswith('.'))):
                    # Check if it looks like a grid line
                    if '+' in l or '|' in l or '.' in l or any(c.isdigit() for c in l) or 'X' in l or '-' in l:
                        grid_lines.append(l)
                        i += 1
                    else:
                        break
                elif l.strip() == '' and grid_lines:
                    break
                elif l.startswith('---') or l.startswith('==='):
                    break
                else:
                    break
            if grid_lines:
                grids.append('\n'.join(grid_lines))
        else:
            i += 1

    return grids

def extract_actions(content):
    """Extract all actions from reasoning file."""
    actions = []
    for line in content.split('\n'):
        if line.startswith('Action:'):
            actions.append(line[7:].strip())
    return actions

def count_edges(grid):
    """Count all edges in a grid."""
    edges = set()
    lines = grid.split('\n')

    for i, line in enumerate(lines):
        if i % 2 == 0:  # Horizontal edge lines
            row = i // 2
            for j in range(0, len(line) - 3, 4):
                if j + 1 < len(line) and line[j+1:j+4] == '---':
                    edges.add(f'H[{row}][{j//4}]')
                if j + 1 < len(line) and line[j+1:j+4] in ['XXX', 'X X']:
                    edges.add(f'B_H[{row}][{j//4}]')  # Blocked horizontal
        else:  # Vertical edge lines
            row = (i - 1) // 2
            for j in range(0, len(line), 4):
                if j < len(line) and line[j] == '|':
                    edges.add(f'V[{row}][{j//4}]')
                if j < len(line) and line[j] == 'X':
                    edges.add(f'B_V[{row}][{j//4}]')  # Blocked vertical

    return edges

def get_edge_diff(grid1, grid2):
    """Get the difference in edges between two grids."""
    edges1 = count_edges(grid1)
    edges2 = count_edges(grid2)

    added = edges2 - edges1
    removed = edges1 - edges2

    return added, removed

def count_endpoints(grid):
    """Count dots with exactly 1 edge (endpoints)."""
    lines = grid.split('\n')
    dot_edges = {}

    # Count edges at each dot
    for i, line in enumerate(lines):
        if i % 2 == 0:  # Horizontal edge lines
            row = i // 2
            for j in range(0, len(line) - 3, 4):
                if j + 1 < len(line) and line[j+1:j+4] == '---':
                    col = j // 4
                    dot_edges[(row, col)] = dot_edges.get((row, col), 0) + 1
                    dot_edges[(row, col+1)] = dot_edges.get((row, col+1), 0) + 1
        else:  # Vertical edge lines
            row = (i - 1) // 2
            for j in range(0, len(line), 4):
                if j < len(line) and line[j] == '|':
                    col = j // 4
                    dot_edges[(row, col)] = dot_edges.get((row, col), 0) + 1
                    dot_edges[(row+1, col)] = dot_edges.get((row+1, col), 0) + 1

    endpoints = [dot for dot, count in dot_edges.items() if count == 1]
    branches = [dot for dot, count in dot_edges.items() if count > 2]

    return endpoints, branches

def check_single_component(grid):
    """Check if all edges form a single connected component."""
    lines = grid.split('\n')
    edges = []

    for i, line in enumerate(lines):
        if i % 2 == 0:  # Horizontal edge lines
            row = i // 2
            for j in range(0, len(line) - 3, 4):
                if j + 1 < len(line) and line[j+1:j+4] == '---':
                    col = j // 4
                    edges.append(((row, col), (row, col+1)))
        else:  # Vertical edge lines
            row = (i - 1) // 2
            for j in range(0, len(line), 4):
                if j < len(line) and line[j] == '|':
                    col = j // 4
                    edges.append(((row, col), (row+1, col)))

    if not edges:
        return True, 0

    adj = {}
    for d1, d2 in edges:
        if d1 not in adj:
            adj[d1] = []
        if d2 not in adj:
            adj[d2] = []
        adj[d1].append(d2)
        adj[d2].append(d1)

    visited = set()
    components = 0

    for start in adj:
        if start not in visited:
            components += 1
            queue = [start]
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                for neighbor in adj.get(node, []):
                    if neighbor not in visited:
                        queue.append(neighbor)

    return components == 1, components

def get_previous_grid(batch_num):
    """Get the final grid from previous batch, or grid_step_0.txt for batch 1."""
    if batch_num == 1:
        return read_file('grid_step_0.txt')
    else:
        prev_reasoning = read_file(f'reasoning_step_{batch_num - 1}.txt')
        if prev_reasoning:
            grids = extract_grids_from_reasoning(prev_reasoning)
            if grids:
                return grids[-1]
    return None

def verify_batch(batch_num):
    """Verify a batch follows all MUST rules."""
    errors = []
    warnings = []

    reasoning_file = f'reasoning_step_{batch_num}.txt'

    # Check 1: File exists
    reasoning_content = read_file(reasoning_file)

    if reasoning_content is None:
        errors.append(f"MISSING: {reasoning_file}")
        return errors, warnings

    # Check 2: Extract actions and grids
    actions = extract_actions(reasoning_content)
    grids = extract_grids_from_reasoning(reasoning_content)

    # Check for BACKTRACK
    has_backtrack = any('BACKTRACK' in a for a in actions)

    # Check 3: Correct number of steps
    if has_backtrack:
        backtrack_idx = next(i for i, a in enumerate(actions) if 'BACKTRACK' in a)
        if backtrack_idx > 0:
            warnings.append(f"BACKTRACK at step {backtrack_idx + 1}")
        expected_steps = backtrack_idx + 1
    else:
        expected_steps = 5

    if len(actions) != expected_steps and not has_backtrack:
        errors.append(f"WRONG STEP COUNT: Expected 5 steps, found {len(actions)}")

    if len(grids) != len(actions):
        errors.append(f"GRID COUNT MISMATCH: {len(actions)} actions but {len(grids)} grids")

    # Check 4: Validator output section present
    if '=== VALIDATOR OUTPUT ===' not in reasoning_content:
        errors.append("MISSING: === VALIDATOR OUTPUT === section")

    # Check 5: Each grid differs by exactly one edge from previous
    prev_grid = get_previous_grid(batch_num)
    if prev_grid:
        all_grids = [prev_grid.strip()] + grids
    else:
        if batch_num == 1:
            errors.append("MISSING: grid_step_0.txt (initial puzzle)")
        all_grids = grids

    for i in range(1, len(all_grids)):
        added, removed = get_edge_diff(all_grids[i-1], all_grids[i])

        # Check if this is a BACKTRACK step
        if i <= len(actions) and 'BACKTRACK' in actions[i-1]:
            # Backtrack can have multiple changes (reverting to earlier state)
            continue

        total_changes = len(added) + len(removed)
        if total_changes == 0:
            errors.append(f"Step {i}: NO CHANGE from previous grid")
        elif total_changes > 1:
            errors.append(f"Step {i}: {total_changes} changes (should be 1). Added: {added}, Removed: {removed}")

    # Check 6: Single path component with 0 or 2 endpoints
    if grids:
        final_grid = grids[-1]
        endpoints, branches = count_endpoints(final_grid)
        is_single, num_components = check_single_component(final_grid)

        if branches:
            errors.append(f"BRANCHING: Dots with 3+ edges: {branches}")

        if len(endpoints) not in [0, 2]:
            errors.append(f"ENDPOINT COUNT: {len(endpoints)} endpoints (must be 0 or 2)")

        if not is_single and num_components > 1:
            errors.append(f"MULTIPLE COMPONENTS: {num_components} disconnected path segments")

        # Check 7: Run the actual validator on final grid
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(final_grid)
            temp_path = f.name

        try:
            result = subprocess.run(
                ['python3', 'validate_grid.py', temp_path, '--check-satisfiability'],
                capture_output=True, text=True
            )

            if result.returncode != 0:
                errors.append(f"VALIDATOR FAILED:\n{result.stdout}{result.stderr}")
        finally:
            os.unlink(temp_path)

    return errors, warnings

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 verify_batch.py <batch_number>")
        sys.exit(1)

    try:
        batch_num = int(sys.argv[1])
    except ValueError:
        print("Error: batch_number must be an integer")
        sys.exit(1)

    print(f"=== Verifying Batch {batch_num} ===\n")

    errors, warnings = verify_batch(batch_num)

    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  ⚠ {w}")
        print()

    if errors:
        print("ERRORS (MUST rule violations):")
        for e in errors:
            print(f"  ✗ {e}")
        print(f"\n=== BATCH {batch_num} FAILED ===")
        sys.exit(1)
    else:
        print(f"✓ All MUST rules satisfied")
        print(f"\n=== BATCH {batch_num} PASSED ===")
        sys.exit(0)

if __name__ == '__main__':
    main()
